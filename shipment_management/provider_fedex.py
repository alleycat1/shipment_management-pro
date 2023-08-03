# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import binascii
import datetime
import json

import frappe
from frappe import _
from frappe.utils import cint
from frappe.utils.file_manager import *
from frappe.utils.password import get_decrypted_password

from shipment_management.config.app_config import PRIMARY_FEDEX_DOC_NAME, ExportComplianceStatement
from shipment_management.shipment import check_permission

# ########################### FEDEX IMPORT ####################################

# IMPORT FEDEX LIBRARY IS WITH <<frappe.get_module>> BECAUSE OF BUG
# Seems like the sandbox import path is broken on certain modules.
# More details: https://discuss.erpnext.com/t/install-requirements-with-bench-problem-importerror/16558/5

# If import error during installation try reinstall fedex manually:
# bench shell
# pip install fedex

# Make sure fedex and all the library file files are there  ~/frappe-bench/env/lib/python2.7/

fedex_track_service = frappe.get_module("fedex.services.track_service")

# TODO - Fix import after https://github.com/python-fedex-devs/python-fedex/pull/86

from shipment_management.temp_fedex.ship_service import FedexDeleteShipmentRequest, FedexProcessInternationalShipmentRequest, FedexProcessShipmentRequest
from shipment_management.temp_fedex.rate_service import FedexRateServiceRequest, FedexInternationalRateServiceRequest

# #############################################################################

# rate_service = frappe.get_module("fedex.services.rate_service")
# ship_service = frappe.get_module("fedex.services.ship_service")
# FedexDeleteShipmentRequest = ship_service.FedexDeleteShipmentRequest
# FedexProcessShipmentRequest = ship_service.FedexProcessShipmentRequest
# FedexRateServiceRequest = rate_service.FedexRateServiceRequest
fedex_config = frappe.get_module("fedex.config")
conversion = frappe.get_module("fedex.tools.conversion")
availability_commitment_service = frappe.get_module("fedex.services.availability_commitment_service")
base_service = frappe.get_module("fedex.base_service")
FedexError = base_service.FedexError
subject_to_json = conversion.sobject_to_json
FedexTrackRequest = fedex_track_service.FedexTrackRequest
FedexConfig = fedex_config.FedexConfig
FedexAvailabilityCommitmentRequest = availability_commitment_service.FedexAvailabilityCommitmentRequest

# #############################################################################


CUSTOMER_TRANSACTION_ID = "*** TrackService Request v10 using Python ***"


def _get_configuration():
	fedex_server_doc_type = frappe.db.sql(
		'''SELECT * from `tabDTI Fedex Configuration` WHERE name = "%s"''' % PRIMARY_FEDEX_DOC_NAME, as_dict=True)

	if not fedex_server_doc_type:
		frappe.throw(_("Please create Fedex Configuration: %s" % PRIMARY_FEDEX_DOC_NAME))

	return fedex_server_doc_type[0]


def get_fedex_server_info():
	fedex_server_doc_type = _get_configuration()

	config_message = """<b>FEDEX CONFIG:</b>
	<br><b>key </b>                   : '{key}'
	<br><b>password </b>              : '{password}'
	<br><b>account_number </b>        : '{account_number}'
	<br><b>meter_number </b>          : '{meter_number}'
	<br><b>freight_account_number</b> : '{freight_account_number}'
	<br><b>use_test_server </b>       : '{use_test_server}'""".format(
		key=fedex_server_doc_type['fedex_key'],
		password=fedex_server_doc_type['password'],
		account_number=fedex_server_doc_type['account_number'],
		meter_number=fedex_server_doc_type['meter_number'],
		freight_account_number=fedex_server_doc_type['freight_account_number'],
		use_test_server=fedex_server_doc_type['use_test_server'])

	return config_message


def get_fedex_config():
	fedex_server_doc_type = _get_configuration()

	if fedex_server_doc_type['use_test_server']:
		_test_server = True
	else:
		_test_server = False

	return FedexConfig(key=fedex_server_doc_type['fedex_key'],
					   password=get_decrypted_password('DTI Fedex Configuration',
													   PRIMARY_FEDEX_DOC_NAME,
													   fieldname='password',
													   raise_exception=True),
					   account_number=fedex_server_doc_type['account_number'],
					   meter_number=fedex_server_doc_type['meter_number'],
					   freight_account_number=fedex_server_doc_type['freight_account_number'],
					   use_test_server=_test_server)


CONFIG_OBJ = get_fedex_config()


# #############################################################################
# #############################################################################
# #############################################################################

@frappe.whitelist()
def estimate_fedex_delivery_time(OriginPostalCode=None,
								 OriginCountryCode=None,
								 DestinationPostalCode=None,
								 DestinationCountryCode=None):

	avc_request = FedexAvailabilityCommitmentRequest(CONFIG_OBJ)

	avc_request.Origin.PostalCode = OriginPostalCode
	avc_request.Origin.CountryCode = OriginCountryCode

	avc_request.Destination.PostalCode = DestinationPostalCode
	avc_request.Destination.CountryCode = DestinationCountryCode

	return avc_request.ShipDate


# #############################################################################
# #############################################################################
# #############################################################################


def create_fedex_package(sequence_number, shipment, box, source_doc):

	items_in_one_box = parse_items_in_box(box)

	# ------------------------

	# Weight:

	package_weight = shipment.create_wsdl_object_of_type('Weight')
	package_weight.Value = get_total_box_value(box=box, source_doc=source_doc, attrib='weight_value')
	package_weight.Units = get_shipment_weight_units(source_doc)
	package = shipment.create_wsdl_object_of_type('RequestedPackageLineItem')
	package.Weight = package_weight

	# ------------------------

	# Insurance:

	package1_insure = shipment.create_wsdl_object_of_type('Money')
	package1_insure.Currency = 'USD'

	package1_insure.Amount = get_total_box_value(box=box, source_doc=source_doc, attrib='insurance')
	package.InsuredValue = package1_insure

	# ------------------------
	if source_doc.signature_option:
		package.SpecialServicesRequested.SpecialServiceTypes = 'SIGNATURE_OPTION'
		package.SpecialServicesRequested.SignatureOptionDetail.OptionType = source_doc.signature_option

	if box.reference_note:
		customer_reference = shipment.create_wsdl_object_of_type('CustomerReference')
		customer_reference.CustomerReferenceType="CUSTOMER_REFERENCE"
		customer_reference.Value = box.reference_note
		package.CustomerReferences.append(customer_reference)

	if box.packaging_type:
		box_doc = frappe.get_doc("Shipping Package", box.packaging_type)
		shipment.RequestedShipment.PackagingType = box_doc.box_code

		package.PhysicalPackaging = box_doc.physical_packaging

		if box_doc.box_code == "YOUR_PACKAGING":
			package_dim = shipment.create_wsdl_object_of_type("Dimensions")
			package_dim.Length = cint(box_doc.length)
			package_dim.Width = cint(box_doc.width)
			package_dim.Height = cint(box_doc.height)
			package_dim.Units = "IN"
			package.Dimensions = package_dim

	package.SequenceNumber = sequence_number

	if source_doc.international_shipment:

		total_box_custom_value = 0

		for i, item in enumerate(items_in_one_box):

			quantity = items_in_one_box[item]

			# ########################

			# Total Insured value exceeds customs value (Error code: 2519)
			# FIX :
			package.InsuredValue.Amount = get_item_by_item_code(source_doc, item).insurance

			# #######################

			# For international multiple piece shipments,
			# commodity information must be passed in the Master and on each child transaction.
			# If this shipment contains more than four commodities line items,
			# the four highest valued should be included in the first 4 occurances for this request.

			commodity = shipment.create_wsdl_object_of_type('Commodity')
			commodity.Name = get_item_by_item_code(source_doc, item).item_name  # Name of this commodity.

			commodity.NumberOfPieces = quantity # Total number of pieces of this commodity

			# Complete and accurate description of this commodity:
			commodity.Description = get_item_by_item_code(source_doc, item).description

			commodity.CountryOfManufacture = source_doc.shipper_address_country_code

			# Weight of this commodity:

			package_weight = shipment.create_wsdl_object_of_type('Weight')
			package_weight.Value = get_item_by_item_code(source_doc, item).weight_value
			package_weight.Units = get_shipment_weight_units(source_doc)
			commodity.Weight = package_weight

			# This field is used for enterprise transactions:
			commodity.Quantity = quantity

			# Unit of measure used to express the quantity of this commodity line item:
			commodity.QuantityUnits = 'EA'

			# Value of each unit in Quantity. Six explicit decimal positions, Max length 18 including decimal:
			commodity.UnitPrice.Currency = "USD"
			commodity.UnitPrice.Amount = get_item_by_item_code(source_doc, item).rate

			# Total customs value for this line item.
			# It should equal the commodity unit quantity times commodity unit value:

			commodity.CustomsValue.Currency = "USD"
			commodity.CustomsValue.Amount = get_item_by_item_code(source_doc, item).custom_value * quantity

			total_box_custom_value += commodity.CustomsValue.Amount

			if commodity.CustomsValue.Amount == 0:
				frappe.throw(_("CUSTOM VALUE = 0. Please specify custom value in items"))

			if commodity.CustomsValue.Amount >= 2500 or source_doc.recipient_address_country_code in ['CA', 'MX']:
				export_detail = shipment.create_wsdl_object_of_type('ExportDetail')
				export_detail.ExportComplianceStatement = ExportComplianceStatement
				shipment.RequestedShipment.CustomsClearanceDetail.ExportDetail = export_detail

			shipment.RequestedShipment.CustomsClearanceDetail.CustomsValue.Amount = commodity.CustomsValue.Amount
			shipment.RequestedShipment.CustomsClearanceDetail.CustomsValue.Currency = commodity.CustomsValue.Currency

			shipment.add_commodity(commodity)

			commodity_message = """<div style="color: #36414c; background-color: #f0f5f5;
			font-size: 80% ; padding: 10px; border-radius: 10px; border: 2px groove;">
			<b>ITEM NAME</b> = {name} <br>
					<b>NUMBER OF PIECES </b>        =  {number_of_pieces}<br>
					<b>DESCRIPTION:</b> <br>
					{description}<br>
					<b>COUNTRY OF MANUFACTURE </b>  =  {country_manufacture}<br>
					<b>WEIGHT  </b>                 =  {weight} <br>
					<b>QUANTITY     </b>            =  {quantity} <br>
					<b>QUANTITY UNITS   </b>        =  {quantity_unites} <br>
					<b>UNIT PRICE CURRENCY    </b>  =  {unit_price_currency} <br>
					<b>UNIT PRICE AMOUNT (RATE) </b>    =  {unit_price_amount} <br>
					<b>CUSTOM VALUE CURRENCY   </b> =  {custom_value_currency} <br>
					<b>TOTAL CUSTOM VALUE AMOUNT    </b>  =  {custom_value_amount} <br></div>
					""".format(box_number=sequence_number,
							   name=commodity.Name,
							   number_of_pieces=commodity.NumberOfPieces,
							   description=commodity.Description,
							   country_manufacture=commodity.CountryOfManufacture,
							   weight="%s %s" % (commodity.Weight.Value, commodity.Weight.Units),
							   quantity=commodity.Quantity,
							   quantity_unites=commodity.QuantityUnits,
							   unit_price_currency=commodity.UnitPrice.Currency,
							   unit_price_amount=commodity.UnitPrice.Amount,
							   custom_value_currency=commodity.CustomsValue.Currency,
							   custom_value_amount=commodity.CustomsValue.Amount)

			if i > 0:
				commodity_message = box.commodity_information + "<br>" + commodity_message

			frappe.db.set(box, 'commodity_information', str(commodity_message))

		frappe.db.set(box, 'total_box_custom_value', total_box_custom_value)


	# -----------------------------

	frappe.db.set(box, 'total_box_insurance', get_total_box_value(box=box,
																  source_doc=source_doc,
																  attrib='insurance'))

	frappe.db.set(box, 'total_box_weight', '%s (%s)' % (get_total_box_value(box=box,
																			source_doc=source_doc,
																			attrib='weight_value'),
														get_shipment_weight_units(source_doc)))

	return package


# #############################################################################
# #############################################################################
# #############################################################################


def create_fedex_shipment(source_doc):
	GENERATE_IMAGE_TYPE = source_doc.file_format

	if source_doc.international_shipment:
		shipment = FedexProcessInternationalShipmentRequest(CONFIG_OBJ, customer_transaction_id=CUSTOMER_TRANSACTION_ID)
		service_type = source_doc.service_type_international
	else:
		shipment = FedexProcessShipmentRequest(CONFIG_OBJ, customer_transaction_id=CUSTOMER_TRANSACTION_ID)
		service_type = source_doc.service_type_domestic

	shipment.RequestedShipment.DropoffType = source_doc.drop_off_type
	shipment.RequestedShipment.ServiceType = service_type

	shipment.RequestedShipment.PackagingType = source_doc.packaging_type

	# Shipper contact info.
	shipment.RequestedShipment.Shipper.Contact.PersonName = source_doc.shipper_contact_person_name
	shipment.RequestedShipment.Shipper.Contact.CompanyName = source_doc.shipper_company_name
	shipment.RequestedShipment.Shipper.Contact.PhoneNumber = source_doc.shipper_contact_phone_number

	# Shipper address.
	shipment.RequestedShipment.Shipper.Address.StreetLines = [source_doc.shipper_address_street_lines]
	shipment.RequestedShipment.Shipper.Address.City = source_doc.shipper_address_city
	shipment.RequestedShipment.Shipper.Address.StateOrProvinceCode = source_doc.shipper_address_state_or_province_code
	shipment.RequestedShipment.Shipper.Address.PostalCode = source_doc.shipper_address_postal_code
	shipment.RequestedShipment.Shipper.Address.CountryCode = source_doc.shipper_address_country_code

	if source_doc.recipient_address_residential:
		shipment.RequestedShipment.Recipient.Address.Residential = True
	else:
		shipment.RequestedShipment.Recipient.Address.Residential = False

	# Recipient contact info.
	shipment.RequestedShipment.Recipient.Contact.PersonName = source_doc.recipient_contact_person_name
	shipment.RequestedShipment.Recipient.Contact.CompanyName = source_doc.recipient_company_name
	shipment.RequestedShipment.Recipient.Contact.PhoneNumber = source_doc.recipient_contact_phone_number

	# Recipient addressStateOrProvinceCode
	shipment.RequestedShipment.Recipient.Address.StreetLines = [source_doc.recipient_address_street_lines]
	shipment.RequestedShipment.Recipient.Address.City = source_doc.recipient_address_city
	shipment.RequestedShipment.Recipient.Address.StateOrProvinceCode = source_doc.recipient_address_state_or_province_code
	shipment.RequestedShipment.Recipient.Address.PostalCode = source_doc.recipient_address_postal_code
	shipment.RequestedShipment.Recipient.Address.CountryCode = source_doc.recipient_address_country_code

	shipment.RequestedShipment.EdtRequestType = 'NONE'

	# Senders account information

	shipment.RequestedShipment.ShippingChargesPayment.Payor.ResponsibleParty.AccountNumber = CONFIG_OBJ.account_number
	shipment.RequestedShipment.ShippingChargesPayment.PaymentType = source_doc.payment_type
	shipment.RequestedShipment.LabelSpecification.LabelFormatType = 'COMMON2D'
	shipment.RequestedShipment.LabelSpecification.ImageType = GENERATE_IMAGE_TYPE
	shipment.RequestedShipment.LabelSpecification.LabelStockType = source_doc.label_stock_type
	shipment.RequestedShipment.ShipTimestamp = datetime.datetime.now().replace(microsecond=0).isoformat()
	shipment.RequestedShipment.LabelSpecification.LabelPrintingOrientation = 'TOP_EDGE_OF_TEXT_FIRST'

	if hasattr(shipment.RequestedShipment.LabelSpecification, 'LabelOrder'):
		del shipment.RequestedShipment.LabelSpecification.LabelOrder  # Delete, not using.

	# #############################################################################

	DictDiffer.validate_shipment_integrity(source_doc)

	# #############################################################################
	# #############################################################################

	all_boxes = source_doc.get_all_children("DTI Shipment Package")

	# The total number of packages in the entire shipment
	# (even when the shipment spans multiple transactions.)
	shipment.RequestedShipment.PackageCount = len(all_boxes)

	# First box

	master_box = all_boxes[0]
	box_sequence_number = 1
	package = create_fedex_package(sequence_number=box_sequence_number,
								   shipment=shipment,
								   box=master_box,
								   source_doc=source_doc)

	shipment.RequestedShipment.RequestedPackageLineItems = [package]

	if source_doc.international_shipment:
		"""
		TotalWeight:
		Identifies the total weight of the shipment being conveyed to FedEx.
		This is only applicable to International shipments
		and should only be used on the first package of a multiple piece shipment.
		This value contains 1 explicit decimal position
		"""
		shipment.RequestedShipment.TotalWeight.Units = get_shipment_weight_units(source_doc)
		shipment.RequestedShipment.TotalWeight.Value = get_total_shipment_value(source_doc=source_doc, attrib='weight_value')

	label = send_request_to_fedex(master_box, shipment, box_sequence_number)

	master_tracking_number = label.TrackingIds[0].TrackingNumber
	master_tracking_id_type = label.TrackingIds[0].TrackingIdType

	frappe.db.set(source_doc, 'tracking_number', master_tracking_number)
	frappe.db.set(source_doc, 'master_tracking_id_type', master_tracking_id_type)
	frappe.db.set(master_box, 'tracking_number', master_tracking_number)

	save_label(label, master_tracking_number, GENERATE_IMAGE_TYPE.lower(), source_doc, master_box, box_sequence_number)

	# ############################################################################
	# ############################################################################

	# For other boxes

	for box in all_boxes[1:]:
		box_sequence_number += 1
		package = create_fedex_package(sequence_number=box_sequence_number,
									   shipment=shipment,
									   box=box,
									   source_doc=source_doc)

		shipment.RequestedShipment.RequestedPackageLineItems = [package]

		shipment.RequestedShipment.MasterTrackingId.TrackingNumber = master_tracking_number
		shipment.RequestedShipment.MasterTrackingId.TrackingIdType = master_tracking_id_type
		label = send_request_to_fedex(box, shipment, box_sequence_number)

		save_label(label, master_tracking_number, GENERATE_IMAGE_TYPE.lower(), source_doc, box, box_sequence_number)

	# ############################################################################
	# ############################################################################
	# ############################################################################
	# ############################################################################

	try:
		delivery_time = estimate_fedex_delivery_time(OriginPostalCode=source_doc.shipper_address_postal_code,
													 OriginCountryCode=source_doc.shipper_address_country_code,
													 DestinationPostalCode=source_doc.recipient_address_postal_code,
													 DestinationCountryCode=source_doc.recipient_address_country_code)
		frappe.db.set(source_doc, 'delivery_time', delivery_time)
		frappe.msgprint("Delivery Time: %s" % delivery_time, "Updated!")
	except Exception as error:
		frappe.throw(_("Delivery time error - %s" % error))

	# ############################################################################
	# ############################################################################

	try:
		rate = get_all_shipment_rate(source_doc.name)
		frappe.db.set(source_doc, 'shipment_rate',
					  """
					  <p style="padding: 15px; align: center; color: #36414c; background-color: #F9FBB6; height: 80px; width: 450px;">
					  TotalNetChargeWithDutiesAndTaxes: <br>
					  <b>%s (%s)</b> </p>
					  """ % (rate["label"], rate["fee"]))

		frappe.msgprint("Rate: %s (%s)" % (rate["label"], rate["fee"]), "Updated!")
	except Exception as error:
		frappe.throw(str(error))
		frappe.db.set(source_doc, 'shipment_rate', "N/A")

	# ############################################################################
	# ############################################################################

	frappe.db.set(source_doc, 'total_insurance',  (get_total_shipment_value(source_doc=source_doc,
																			attrib='insurance')))

	if source_doc.international_shipment:
		frappe.db.set(source_doc, 'total_custom_value', sum([box.total_box_custom_value for box in all_boxes]))

	frappe.db.set(source_doc, 'total_weight', '%s (%s)' % (get_total_shipment_value(source_doc=source_doc,
																					attrib='weight_value'),
														   get_shipment_weight_units(source_doc)))

	# #############################################################################
	# #############################################################################

	frappe.msgprint("DONE!", "Tracking number:{}".format(master_tracking_number))


# #############################################################################
# #############################################################################

def save_label(label, master_tracking_number, image_type, source_doc, box, box_sequence_number):
	box_tracking_number = label.TrackingIds[0].TrackingNumber
	ascii_label_data = label.Label.Parts[0].Image
	label_binary_data = binascii.a2b_base64(ascii_label_data)

	frappe.db.set(box, 'tracking_number', box_tracking_number)

	file_name = "label_%s_%s.%s" % (master_tracking_number, box_tracking_number, image_type)
	saved_file = save_file(file_name, label_binary_data, source_doc.doctype, source_doc.name, is_private=1)
	frappe.db.set(source_doc, 'label_%i' % box_sequence_number, saved_file.file_url)

# #############################################################################
# #############################################################################


def send_request_to_fedex(box, shipment, box_sequence_number):
	try:
		shipment.send_request()
		return shipment.response.CompletedShipmentDetail.CompletedPackageDetails[0]

	except Exception as error:
		if "Customs Value is required" in str(error):
			frappe.throw(_("International Shipment option is required".upper()))
		else:
			frappe.throw(_("[BOX # {}] Error from Fedex: {}".format(box_sequence_number, str(error))))

# #############################################################################
# #############################################################################


def get_shipment_weight_units(source_doc):
	weight_units = set()

	for box in source_doc.box_list:
		items = parse_items_in_box(box)
		for item in items:
			weight_units.add(get_item_by_item_code(source_doc, item).weight_units)

		if len(weight_units) > 1:
			frappe.throw(_("Please select the same weight units for all items. They can't be different."))

	return weight_units.pop()

# #############################################################################
# #############################################################################


def get_total_box_value(box, source_doc, attrib):
	"""
	Fox insurance, weight and etc. calculation for box
	"""
	box_total = 0
	items = parse_items_in_box(box)
	for item in items:
		quantity_in_box = items[item]
		box_total += getattr(get_item_by_item_code(source_doc=source_doc, item_code=item), attrib) * quantity_in_box


	if attrib == "weight_value":
		box_total += frappe.get_value("Shipping Package", box.packaging_type, "weight")
	return box_total


def get_total_shipment_value(source_doc, attrib):
	"""
	Fox insurance, weight  and etc.calculation for all shipment
	"""
	return sum([get_total_box_value(box, source_doc, attrib) for box in source_doc.box_list])

# #############################################################################
# #############################################################################


def parse_items_in_box(box):
	items = {}
	lines = box.items_in_box.split("\n")
	for line in lines:
		try:
			item = line.split(":")
		except ValueError:
			frappe.msgprint(_("WARNING! Bad lines:%s" % line))

		if item[0] in items:
			items[item[0]] += int(item[1])
		else:
			items.update({item[0]: int(item[1])})
	return items


# #############################################################################
# #############################################################################

def get_item_by_item_code(source_doc, item_code):
	all_delivery_items = source_doc.get_all_children("DTI Shipment Note Item")

	for item in all_delivery_items:
		if item.item_code == item_code:
			return item

# #############################################################################
# #############################################################################

@frappe.whitelist()
def get_fedex_packages_rate(international=False,
							DropoffType=None,
							ServiceType=None,
							PackagingType=None,
							ShipperStateOrProvinceCode=None,
							ShipperPostalCode=None,
							ShipperCountryCode=None,
							RecipientStateOrProvinceCode=None,
							RecipientPostalCode=None,
							RecipientCountryCode=None,
							EdtRequestType=None,
							IsResidential=False,
							PaymentType=None,
							package_list=None,
							ignoreErrors=False,
							single_rate=False,
							signature_option=None,
							exceptions=None,
							delivery_date=None,
							saturday_delivery=False,
							flat_rate=False):

	"""
	:param international:
	:param DropoffType:
	:param ServiceType:
	:param PackagingType:
	:param ShipperStateOrProvinceCode:
	:param ShipperPostalCode:
	:param ShipperCountryCode:
	:param RecipientStateOrProvinceCode:
	:param RecipientPostalCode:
	:param RecipientCountryCode:
	:param EdtRequestType:
	:param PaymentType:
	:param package_list:
	:return: data rate

	EXAMPLE

	DropoffType: 'REGULAR_PICKUP',
	ServiceType:'FEDEX_GROUND',
	PackagingType: 'YOUR_PACKAGING',
	ShipperStateOrProvinceCode:'SC',
	ShipperPostalCode: '29631',
	ShipperCountryCode:'US',
	RecipientStateOrProvinceCode:'NC',
	RecipientPostalCode:'27577',
	RecipientCountryCode:'US',
	EdtRequestType:'NONE',
	PaymentType:'SENDER',
	package_list:
	[{"weight_value":"1",
	"weight_units":"LB",
	"physical_packaging":"BOX",
	"group_package_count":"1",
	"insured_amount":"100"},
	{"weight_value":"10004000",
	"weight_units":"LB",
	"physical_packaging":"BOX",
	"group_package_count":"2",
	"insured_amount":"100"}]

	_______________________________

	KNOWN ISSUES (FEDEX TEST SERVER)

	Test server caches rate for the same Shipper/Recipient data

	"""

	# Initiate Fedex request
	if international:
		rate = FedexInternationalRateServiceRequest(CONFIG_OBJ)
	else:
		rate = FedexRateServiceRequest(CONFIG_OBJ)

	# Set Fedex shipping details
	rate.RequestedShipment.DropoffType = DropoffType
	rate.RequestedShipment.ServiceType = ServiceType
	rate.RequestedShipment.PackagingType = PackagingType

	# Set shipper address details
	rate.RequestedShipment.Shipper.Address.StateOrProvinceCode = ShipperStateOrProvinceCode
	rate.RequestedShipment.Shipper.Address.PostalCode = ShipperPostalCode
	rate.RequestedShipment.Shipper.Address.CountryCode = ShipperCountryCode

	# Set reciever address details
	if RecipientStateOrProvinceCode:
		rate.RequestedShipment.Recipient.Address.StateOrProvinceCode = RecipientStateOrProvinceCode
	rate.RequestedShipment.Recipient.Address.PostalCode = RecipientPostalCode
	rate.RequestedShipment.Recipient.Address.CountryCode = RecipientCountryCode
	rate.RequestedShipment.Recipient.Address.Residential = IsResidential

	# Set payer details
	rate.RequestedShipment.EdtRequestType = EdtRequestType
	rate.RequestedShipment.ShippingChargesPayment.PaymentType = PaymentType

	# Set special services, if applicable

	# Fedex One Rate
	if flat_rate:
		rate.RequestedShipment.SpecialServicesRequested.SpecialServiceTypes = "FEDEX_ONE_RATE"

	# Fedex Saturday Delivery
	elif saturday_delivery:
		if not delivery_date:
			frappe.throw(_("Please specify Ship Date for Saturday Delivery"))

		delivery_datetime = frappe.utils.get_datetime(delivery_date)
		rate.RequestedShipment.SpecialServicesRequested.SpecialServiceTypes = "SATURDAY_DELIVERY"
		rate.RequestedShipment.ShipTimestamp = delivery_datetime.isoformat()

	# Create Fedex shipments for each package
	for package in package_list:
		# Set package weights
		pkg_weight = rate.create_wsdl_object_of_type('Weight')
		pkg_weight.Value = package["weight_value"]
		pkg_weight.Units = package["weight_units"]

		# Set package content details
		pkg_obj = rate.create_wsdl_object_of_type('RequestedPackageLineItem')
		pkg_obj.Weight = pkg_weight
		pkg_obj.GroupPackageCount = package["group_package_count"]

		# Set packaging details
		if flat_rate:
			rate.RequestedShipment.PackagingType = PackagingType
			pkg_obj.PhysicalPackaging = frappe.db.get_value("Shipping Package", {"box_code": PackagingType}, "physical_packaging")
		elif package.get("packaging_type"):
			box_doc = frappe.get_doc("Shipping Package", package.get("packaging_type"))
			rate.RequestedShipment.PackagingType = box_doc.box_code
			pkg_obj.PhysicalPackaging = box_doc.physical_packaging

			if box_doc.box_code == "YOUR_PACKAGING":
				pkg_dim = rate.create_wsdl_object_of_type("Dimensions")
				pkg_dim.Length = cint(box_doc.length)
				pkg_dim.Width = cint(box_doc.width)
				pkg_dim.Height = cint(box_doc.height)
				pkg_dim.Units = "IN"
				pkg_obj.Dimensions = pkg_dim

		# Set insurance amounts
		pkg_insurance = rate.create_wsdl_object_of_type('Money')
		pkg_insurance.Currency = "USD"
		pkg_insurance.Amount = package["insured_amount"]
		pkg_obj.InsuredValue = pkg_insurance

		# Set additional surcharges
		if signature_option:
			pkg_obj.SpecialServicesRequested.SpecialServiceTypes = 'SIGNATURE_OPTION'
			pkg_obj.SpecialServicesRequested.SignatureOptionDetail.OptionType = signature_option

		rate.add_package(pkg_obj)

	try:
		# Get rates for all the packages
		rate.send_request()
	except Exception as e:
		print(e)

		if exceptions is not None:
			exceptions.append({"type": "request", "exception": e})

		if 'RequestedPackageLineItem object cannot be null or empty' in str(e):
			raise Exception("WARNING: Please create packages with shipment")
		elif not ignoreErrors:
			frappe.throw(str(e))

		return None

	response_json = subject_to_json(rate.response)
	data = json.loads(response_json)

	if "Service is not allowed" in str(data['Notifications'][0]['Message']):
		if ignoreErrors:
			return None

		debug_info = "%s <br> %s <br> %s" % (rate.RequestedShipment.ServiceType, rate.RequestedShipment.Shipper, rate.RequestedShipment.Recipient)

		frappe.throw(_("WARNING: Service is not allowed. Please verify address data! <br> % s" % debug_info))

	rates = []

	try:
		for service in data["RateReplyDetails"]:
			rates.append({
				'fee': service['RatedShipmentDetails'][0]['ShipmentRateDetail']['TotalNetChargeWithDutiesAndTaxes']['Amount'],
				'label' : service['ServiceType'].replace("_", " "),
				'name' : service['ServiceType'],
				'special_rates_applied': service['RatedShipmentDetails'][0]['ShipmentRateDetail'].get('SpecialRatingApplied', [])
			})
	except KeyError as e:
		if exceptions is not None:
			exceptions.append({"type": "keyerror", "exception": e})
		if not ignoreErrors:
			frappe.throw(data)
		return

	if single_rate:
		return rates[0]
	else:
		return rates

@frappe.whitelist()
def get_all_shipment_rate(doc_name):
	source_doc = frappe.get_doc("DTI Shipment Note", doc_name)
	BOXES = source_doc.get_all_children("DTI Shipment Package")

	rate_box_list = []
	for i, box in enumerate(BOXES):
		box_weight_value = get_total_box_value(box=box, source_doc=source_doc, attrib='weight_value')
		box_weight_units = get_shipment_weight_units(source_doc)

		box_insurance = get_total_box_value(box=box, source_doc=source_doc, attrib='insurance')

		rate_box_list.append({'weight_value': box_weight_value,
							  'weight_units': box_weight_units,
							  'physical_packaging': box.physical_packaging,
							  'packaging_type': box.packaging_type,
							  'group_package_count': i+1,
							  'insured_amount': box_insurance})

	if source_doc.international_shipment:
		service_type = source_doc.service_type_international
	else:
		service_type = source_doc.service_type_domestic

	return get_fedex_packages_rate(international=source_doc.international_shipment,
								   DropoffType=source_doc.drop_off_type,
								   ServiceType=service_type,
								   PackagingType=source_doc.packaging_type,
								   ShipperStateOrProvinceCode=source_doc.shipper_address_state_or_province_code,
								   ShipperPostalCode=source_doc.shipper_address_postal_code,
								   ShipperCountryCode=source_doc.shipper_address_country_code,
								   RecipientStateOrProvinceCode=source_doc.recipient_address_state_or_province_code,
								   RecipientPostalCode=source_doc.recipient_address_postal_code,
								   RecipientCountryCode=source_doc.recipient_address_country_code,
								   IsResidential=source_doc.recipient_address_residential,
								   EdtRequestType='NONE',
								   PaymentType=source_doc.payment_type,
								   package_list=rate_box_list,
								   signature_option=source_doc.signature_option,
								   single_rate=True)

# #############################################################################
# #############################################################################


@frappe.whitelist()
def show_shipment_estimates(doc_name):
	"""
	Fedex's shipping calculator estimates the time and cost of delivery based on the destination and service.
	"""
	source_doc = frappe.get_doc("DTI Shipment Note", doc_name)

	DictDiffer.validate_shipment_integrity(source_doc=source_doc)

	frappe.msgprint("Shipment calculator estimates the time and cost of delivery based on the destination and service.",
					"INFO")

	# ===============================================================

	# Delivery time

	time = estimate_fedex_delivery_time(OriginPostalCode=source_doc.recipient_address_postal_code,
										OriginCountryCode=source_doc.recipient_address_postal_code,
										DestinationPostalCode=source_doc.shipper_address_country_code,
										DestinationCountryCode=source_doc.shipper_address_postal_code)

	frappe.msgprint("<b>Delivery time</b> : %s" % time, "INFO")

	# ===============================================================

	# Calculate Rate:

	rate_box_list = []
	for i, box in enumerate(source_doc.get_all_children("DTI Shipment Package")):

		box_weight_value = get_total_box_value(box=box, source_doc=source_doc, attrib='weight_value')
		box_weight_units = get_shipment_weight_units(source_doc)

		box_insurance = get_total_box_value(box=box, source_doc=source_doc, attrib='insurance')

		rate_box_list.append({'weight_value': box_weight_value,
							  'weight_units': box_weight_units,
							  'physical_packaging': box.physical_packaging,
							  'packaging_type' : box.packaging_type,
							  'group_package_count': i+1,
							  'insured_amount': box_insurance})

	# TODO - Remove YOUR_PACKAGING and use real PackagingType from doc, investigate error:
	# Service is not allowed. (Code = 868)

	rates = get_fedex_packages_rate(international=source_doc.international_shipment,
									DropoffType=source_doc.drop_off_type,
									PackagingType='YOUR_PACKAGING',
									ShipperStateOrProvinceCode=source_doc.shipper_address_state_or_province_code,
									ShipperPostalCode=source_doc.shipper_address_postal_code,
									ShipperCountryCode=source_doc.shipper_address_country_code,
									RecipientStateOrProvinceCode=source_doc.recipient_address_state_or_province_code,
									RecipientPostalCode=source_doc.recipient_address_postal_code,
									RecipientCountryCode=source_doc.recipient_address_country_code,
									EdtRequestType='NONE',
									IsResidential=source_doc.recipient_address_residential,
									signature_option=source_doc.signature_option,
									PaymentType=source_doc.payment_type,
									package_list=rate_box_list)

	for rate in rates:
		frappe.msgprint("<b>%s</b> : %s (%s)<br>" % (rate["label"], rate["fee"], "USD"))


# #############################################################################
# #############################################################################

def delete_fedex_shipment(source_doc):
	del_request = FedexDeleteShipmentRequest(CONFIG_OBJ)
	del_request.DeletionControlType = "DELETE_ALL_PACKAGES"
	del_request.TrackingId.TrackingNumber = source_doc.tracking_number
	del_request.TrackingId.TrackingIdType = source_doc.master_tracking_id_type

	try:
		del_request.send_request()
	except Exception as e:
		if 'Unable to retrieve record' in str(e):
			raise Exception("WARNING: Unable to delete the shipment with the provided tracking number.")
		else:
			raise Exception("ERROR: %s. Tracking number: %s. Type: %s" % (e, source_doc.tracking_number, source_doc.master_tracking_id_type))


# #############################################################################
# #############################################################################


def get_fedex_shipment_status(track_value):
	track = FedexTrackRequest(CONFIG_OBJ, customer_transaction_id=CUSTOMER_TRANSACTION_ID)

	track.SelectionDetails.PackageIdentifier.Type = 'TRACKING_NUMBER_OR_DOORTAG'
	track.SelectionDetails.PackageIdentifier.Value = track_value

	del track.SelectionDetails.OperatingCompany

	try:
		track.send_request()
		return track.response[4][0].TrackDetails[0].Events[0].EventDescription
	except AttributeError:
		return None
	except FedexError as error:
		frappe.throw(_("Fedex error! {} {}".format(error, get_fedex_server_info())))


# #############################################################################
# #############################################################################


@frappe.whitelist(allow_guest=True)
def get_html_code_status_with_fedex_tracking_number(track_value):
	"""
	FOR WEB PAGE WITH SHIPMENT TRACKING - shipment_tracking.html
	:param track_value:
	:return:
	"""
	if not track_value:
		return "Track value can't be empty"

	track = FedexTrackRequest(CONFIG_OBJ, customer_transaction_id=CUSTOMER_TRANSACTION_ID)

	track.SelectionDetails.PackageIdentifier.Type = 'TRACKING_NUMBER_OR_DOORTAG'
	track.SelectionDetails.PackageIdentifier.Value = track_value

	del track.SelectionDetails.OperatingCompany

	try:
		track.send_request()
		html = ""

		for match in track.response.CompletedTrackDetails[0].TrackDetails:
			html += "<b>Tracking #:</b> {}".format(match.TrackingNumber)

			if hasattr(match, 'TrackingNumberUniqueIdentifier'):
				html += "<br><b>UniqueID:</b> {}".format(match.TrackingNumberUniqueIdentifier)

			if hasattr(match, 'Notification'):
				html += "<br>{}".format(match.Notification.Message)

			if hasattr(match, 'StatusDetail.Description'):
				html += "<br>Status Description: {}".format(match.StatusDetail.Description)

			if hasattr(match, 'StatusDetail.AncillaryDetails'):
				html += "<br>Status AncillaryDetails Reason: {}".format(match.StatusDetail.AncillaryDetails[-1].Reason)
				html += "<br>Status AncillaryDetails Description: {}".format(
					match.StatusDetail.AncillaryDetails[-1].ReasonDescription)

			if hasattr(match, 'ServiceCommitMessage'):
				html += "<br><b>{}</b>".format(match.ServiceCommitMessage)

			html += "<br><br>"

		return html

	except Exception as error:
		return """<b>ERROR :</b><br> Fedex invalid configuration error! <br>{0}<br><br>{1} """.format(error.value,
																									  get_fedex_server_info())

# #############################################################################
# #############################################################################


class DictDiffer(object):
	"""
	Calculate the difference between two dictionaries as:
	(1) items added
	(2) items removed
	(3) keys same in both but changed values
	(4) keys same in both and unchanged values
	"""
	def __init__(self, current_dict, past_dict):
		self.current_dict, self.past_dict = current_dict, past_dict
		self.set_current, self.set_past = set(current_dict.keys()), set(past_dict.keys())
		self.intersect = self.set_current.intersection(self.set_past)

	def added(self):
		return self.set_current - self.intersect

	def removed(self):
		return self.set_past - self.intersect

	def changed(self):
		return set(o for o in self.intersect if self.past_dict[o] != self.current_dict[o])

	def unchanged(self):
		return set(o for o in self.intersect if self.past_dict[o] == self.current_dict[o])

	@staticmethod
	def validate_shipment_integrity(source_doc):
		"""
		Basic validation that shipment is correct.
		That all items from delivery note are in boxes and etc.
		"""

		boxes = source_doc.get_all_children("DTI Shipment Package")

		if len(boxes) > 9:
			frappe.throw(_("Max amount of packages is 10"))

		if not boxes:
			frappe.throw(_("Please create shipment box packages!"))

		parsed_items_per_box = {i: parse_items_in_box(package) for i, package in enumerate(boxes)}
		all_items_in_all_boxes = {}
		for box in parsed_items_per_box:
			for item_code in parsed_items_per_box[box]:
				if item_code in all_items_in_all_boxes:
					all_items_in_all_boxes[item_code] += parsed_items_per_box[box][item_code]
				else:
					all_items_in_all_boxes.update({item_code: int(parsed_items_per_box[box][item_code])})

		delivery_items_dict = {}
		for item in source_doc.get_all_children("DTI Shipment Note Item"):
			if item.item_code in delivery_items_dict:
				delivery_items_dict[item.item_code] += int(item.qty)
			else:
				delivery_items_dict.update({item.item_code: int(item.qty)})

		differ = DictDiffer(delivery_items_dict, all_items_in_all_boxes)

		if differ.changed():
			delivery_string = "<br>".join("%s = %i" % (item, delivery_items_dict[item]) for item in delivery_items_dict)
			all_items_string = "<br>".join(
				"%s = %i" % (item, all_items_in_all_boxes[item]) for item in all_items_in_all_boxes)

			error_message = """<b style="color:orange;">WARNING!</b><br>
			Integrity error for: <b>{}</b> <br>
			<hr>
			<b>DELIVERY ITEMS:</b> <br>{} <br><br>
			<b>ITEMS IN BOX:</b> <br>{}""".format(",".join(differ.changed()), delivery_string, all_items_string)

			frappe.throw(_(error_message))
