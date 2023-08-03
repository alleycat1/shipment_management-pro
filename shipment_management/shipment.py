# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_company_address
from frappe.model.document import get_doc
from frappe.model.mapper import get_mapped_doc
from frappe.utils import add_months, now

from shipment_management.config.app_config import PRIMARY_FEDEX_DOC_NAME, FedexTestServerConfiguration, StatusMapFedexAndShipmentNote, SupportedProviderList
from shipment_management.utils import get_country_code

def check_permission(fn):
	def innerfn(*args, **kwargs):
		for role in ["Shipment Management Admin", "Shipment Management User", "Admin", "Administrator"]:
			if str(role) in frappe.get_roles():
				break
			frappe.throw(_("Permission denied for = {}".format(frappe.session.user)), frappe.PermissionError)
		return fn(*args, **kwargs)

	return innerfn


def after_install():
	"""
	Creation Test Server Configuration for debug and testing during Application Development
	"""

	FedexConfig = frappe.new_doc("DTI Fedex Configuration")

	FedexConfig.fedex_config_name = PRIMARY_FEDEX_DOC_NAME
	FedexConfig.fedex_key = FedexTestServerConfiguration.key
	FedexConfig.password = FedexTestServerConfiguration.password
	FedexConfig.account_number = FedexTestServerConfiguration.account_number
	FedexConfig.meter_number = FedexTestServerConfiguration.meter_number
	FedexConfig.freight_account_number = FedexTestServerConfiguration.freight_account_number
	FedexConfig.use_test_server = FedexTestServerConfiguration.use_test_server

	FedexConfig.submit()


class ShipmentNoteOperationalStatus(object):
	Created = "ReadyToPickUp"
	InProgress = "In progress"
	Completed = "Completed"
	Cancelled = "Cancelled"
	Failed = "Failed"


##############################################################################
@frappe.whitelist()
def get_sales_order(delivery_note_name):
	against_sales_order = frappe.get_all("Delivery Note Item", filters={"parent": delivery_note_name}, fields=["against_sales_order"])
	if against_sales_order:
		return against_sales_order[0]


##############################################################################


@frappe.whitelist()
def get_carriers_list():
	return [SupportedProviderList.Fedex]


##############################################################################


class Contact(object):
	def __init__(self):
		self.PersonName = None
		self.CompanyName = None
		self.PhoneNumber = None
		self.Email_List = []


class Address(object):
	def __init__(self):
		self.StreetLines = []
		self.City = None
		self.StateOrProvinceCode = None
		self.PostalCode = None
		self.Country = None
		self.CountryCode = None
		self.Residential = None


class RequestedShipment(object):
	def __init__(self):
		self.address = Address()
		self.contact = Contact()

	def __str__(self):
		return """
		Contact PersonName            = {0}
		Contact CompanyName           = {1}
		Contact PhoneNumber           = {2}
		Email list                    = {3}
		___________________________________________

		Address StreetLines           = {4}
		Address City                  = {5}
		Address StateOrProvinceCode   = {6}
		Address PostalCode            = {7}
		Address Country               = {8}
		Address CountryCode           = {9} """.format(self.contact.PersonName,
													   self.contact.CompanyName,
													   self.contact.PhoneNumber,
													   self.contact.Email_List,
													   self.address.StreetLines,
													   self.address.City,
													   self.address.StateOrProvinceCode,
													   self.address.PostalCode,
													   self.address.Country,
													   self.address.CountryCode)


def get_shipper(delivery_note_name):
	shipper = RequestedShipment()

	delivery_note_company = frappe.db.get_value("Delivery Note", delivery_note_name, "company")

	if delivery_note_company:
		shipper.contact.PersonName = delivery_note_company
		shipper.contact.CompanyName = delivery_note_company

		company = frappe.db.get_values("Company", delivery_note_company, ["phone_no", "country"], as_dict=True)

		if company:
			shipper.contact.PhoneNumber = company[0].phone_no
			shipper.address.Country = company[0].country
			shipper.address.CountryCode = get_country_code(shipper.address.Country)

			shipper_address = None
			company_address = get_company_address(delivery_note_company).company_address

			if company_address:
				shipper_address = frappe.get_doc("Address", company_address)

			if shipper_address:
				shipper.address.StreetLines.append(shipper_address.address_line1)

				if shipper_address.address_line2:
					shipper.address.StreetLines.append(shipper_address.address_line2)

				shipper.address.City = shipper_address.city
				shipper.address.PostalCode = shipper_address.pincode
				shipper.address.StateOrProvinceCode = shipper_address.state

	return shipper


def get_recipient(delivery_note_name):
	recipient = RequestedShipment()
	recipient.contact.CompanyName = frappe.db.get_value("Delivery Note", delivery_note_name, "customer")

	contact_person = frappe.db.get_value("Delivery Note", delivery_note_name, "contact_person")

	if contact_person:
		primary_contact = frappe.get_doc("Contact", contact_person)
	else:
		primary_contact = frappe.get_doc({
			"doctype": "Contact",
			"is_primary_contact": 1,
			"links": [{
				"link_doctype": "Customer",
				"link_name": recipient.contact.PersonName
			}]
		})

	if frappe.db.exists("Contact", primary_contact.name):
		if not recipient.contact.PhoneNumber:
			person_name = primary_contact.first_name

			if primary_contact.last_name:
				person_name += " {}".format(primary_contact.last_name)

			recipient.contact.PersonName = person_name
			recipient.contact.PhoneNumber = primary_contact.phone

	delivery_address = frappe.db.get_value("Delivery Note", delivery_note_name, "shipping_address_name")

	if delivery_address:
		shipping_address = frappe.get_doc("Address", delivery_address)

		if shipping_address.email_id:
			recipient.contact.Email_List.append(shipping_address.email_id)

		recipient.address.StreetLines.append(shipping_address.address_line1)

		if shipping_address.address_line2:
			recipient.address.StreetLines.append(shipping_address.address_line2)

		recipient.address.City = shipping_address.city
		recipient.address.PostalCode = shipping_address.pincode

		recipient.address.Country = shipping_address.country
		recipient.address.CountryCode = get_country_code(recipient.address.Country)

		recipient.address.StateOrProvinceCode = shipping_address.state
		recipient.address.Residential = shipping_address.is_residential

		if primary_contact.email_id and (primary_contact.email_id != shipping_address.email_id):
			recipient.contact.Email_List.append(primary_contact.email_id)

	return recipient


@frappe.whitelist()
def get_recipient_details(delivery_note_name):
	recipient = get_recipient(delivery_note_name)

	return {"recipient_contact_person_name": recipient.contact.PersonName or "",
			"recipient_company_name": recipient.contact.CompanyName or "",
			"recipient_contact_phone_number": recipient.contact.PhoneNumber or "",
			"recipient_address_street_lines": " ".join(recipient.address.StreetLines),
			"recipient_address_city": recipient.address.City or "",
			"recipient_address_state_or_province_code": recipient.address.StateOrProvinceCode or "",
			"recipient_address_country_code": recipient.address.CountryCode or "",
			"recipient_address_postal_code": recipient.address.PostalCode or "",
			"recipient_address_residential" : recipient.address.Residential or "",
			"contact_email": ", ".join(recipient.contact.Email_List)}


@frappe.whitelist()
def get_shipper_details(delivery_note_name):
	shipper = get_shipper(delivery_note_name)
	return {"shipper_contact_person_name": shipper.contact.PersonName or "",
			"shipper_company_name": shipper.contact.CompanyName or "",
			"shipper_contact_phone_number": shipper.contact.PhoneNumber or "",
			"shipper_address_street_lines": " ".join(shipper.address.StreetLines) or "",
			"shipper_address_city": shipper.address.City or "",
			"shipper_address_state_or_province_code": shipper.address.StateOrProvinceCode or "",
			"shipper_address_country_code": shipper.address.CountryCode or "",
			"shipper_address_postal_code": shipper.address.PostalCode or ""}


##############################################################################


@frappe.whitelist()
def get_delivery_items(delivery_note_name):
	return frappe.get_all("Delivery Note Item", filters={"parent": delivery_note_name}, fields=["*"])


##############################################################################
##############################################################################
##############################################################################

@frappe.whitelist()
def shipment_status_update_controller():
	from provider_fedex import get_fedex_shipment_status

	filters = {
		"docstatus": 1,
		"fedex_status": ["not in", ["Delivered", "Shipment cancelled by sender"]],
		"creation": ["between", [add_months(now(), -2), now()]]
	}

	all_ships = frappe.get_all("DTI Shipment Note", filters=filters, fields=["name", "fedex_status", "tracking_number"])

	for ship in all_ships:
		latest_status = get_fedex_shipment_status(ship.tracking_number)

		if latest_status and latest_status != ship.fedex_status:
			frappe.db.set_value("DTI Shipment Note", ship.name, "fedex_status", latest_status, update_modified=False)
			frappe.db.commit()

##############################################################################
##############################################################################
##############################################################################

@frappe.whitelist()
def make_new_shipment_note_from_delivery_note(source_name, target_doc=None):
	doclist = get_mapped_doc("Delivery Note", source_name, {
		"Delivery Note": {
			"doctype": "DTI Shipment Note",
			"field_map": {
				"name": "delivery_note",
			}
		}
	}, target_doc)

	recipient = get_recipient(source_name)
	shipper = get_shipper(source_name)

	items = get_delivery_items(source_name)

	doclist.update({"recipient_contact_person_name": recipient.contact.PersonName or "",
			"recipient_company_name": recipient.contact.CompanyName or "",
			"recipient_contact_phone_number": recipient.contact.PhoneNumber or "",
			"recipient_address_street_lines": " ".join(recipient.address.StreetLines),
			"recipient_address_city": recipient.address.City or "",
			"recipient_address_state_or_province_code": recipient.address.StateOrProvinceCode or "",
			"recipient_address_country_code": recipient.address.CountryCode or "",
			"recipient_address_postal_code": recipient.address.PostalCode or "",
			"contact_email": ", ".join(recipient.contact.Email_List),
	 		"shipper_contact_person_name": shipper.contact.PersonName or "",
			"shipper_company_name": shipper.contact.CompanyName or "",
			"shipper_contact_phone_number": shipper.contact.PhoneNumber or "",
			"shipper_address_street_lines": " ".join(shipper.address.StreetLines) or "",
			"shipper_address_city": shipper.address.City or "",
			"shipper_address_state_or_province_code": shipper.address.StateOrProvinceCode or "",
			"shipper_address_country_code": shipper.address.CountryCode or "",
			"shipper_address_postal_code": shipper.address.PostalCode or "",
			"delivery_items": items,
	})

	return doclist
