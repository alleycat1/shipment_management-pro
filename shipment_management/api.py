from __future__ import unicode_literals

import json
from math import ceil

import frappe

from shipment_management.provider_fedex import get_fedex_packages_rate
from shipment_management.utils import get_country_code


@frappe.whitelist()
def get_rates_for_doc(doc, address=None, address_obj=None):
	doc = json.loads(doc)
	from frappe.contacts.doctype.address.address import get_address_display
	if not address_obj:
		to_address = frappe.get_doc("Address", address or doc.get("shipping_address_name"))
		frappe.local.response["address"] = get_address_display(to_address.as_dict())
	else:
		to_address = json.loads(address_obj)
		frappe.local.response["address"] = get_address_display(to_address)


	from_address = frappe.get_doc("Address", {"is_your_company_address" : 1})
	return get_rates(from_address, to_address, doc=doc)


def get_rates(from_address, to_address, items=None, doc=None, packaging_type="YOUR_PACKAGING"):
	"""Simple wrapper over fedex rating service.

	It takes the standard address field values for the from_ and to_ addresses
	to keep a consistent address api.
	"""

	# quick hack to package all items into one box for quick shipping quotations
	# packages = find_packages(items)
	packages = []
	package = {
		"weight_value": 0,
		"weight_units": "LB",
		"physical_packaging": "BOX",
		"group_package_count": 0,
		"insured_amount": 0
	}

	item_values = frappe.get_all("Item", fields=["insured_declared_value", "name", "net_weight"])
	item_values = {elem.pop("name"): elem for elem in item_values}

	if doc and not items:
		items = doc.get("items")

	# Set the item weights, quantity and insured amounts in the package(s).
	# For repairs, only process packages once for each warranty claim.
	processed_claims = []
	weight_value = group_package_count = insured_amount = 0
	for item in items:
		if item.get("warranty_claim") and item.get("warranty_claim") not in processed_claims:
			repair_items = frappe.db.get_value("Warranty Claim", item.get("warranty_claim"), ["item_code", "cable", "case"])
			repair_items = list(filter(None, repair_items))
			group_package_count = len(repair_items)

			for repair_item in repair_items:
				weight_value += item_values.get(repair_item, {}).get("net_weight", 0)
				insured_amount += item_values.get(repair_item, {}).get("insured_declared_value", 0)

			processed_claims.append(item.get("warranty_claim"))
		else:
			group_package_count += item.get("qty", 0)
			weight_value += item_values.get(item.get("item_code"), {}).get("net_weight", 0) * item.get("qty", 0)
			insured_amount += item_values.get(item.get("item_code"), {}).get("insured_declared_value", 0) * item.get("qty", 0)

	package["weight_value"] = max(1, ceil(weight_value))
	package["group_package_count"] = group_package_count
	package["insured_amount"] = insured_amount
	packages.append(package)

	# to try and keep some form of standardization we'll minimally require
	# a weight_value. Any other values will be passed as is to the rates service.
	surcharge = 0
	for package in packages:
		if package.get("weight_value") is None or package.get("weight_units") is None:
			raise frappe.exceptions.ValidationError("Missing weight_value data")

		# if not package.get("group_package_count"):
		# keep count on 1 as we don't care about package groups
		package["group_package_count"] = 1

		if not package.get("insured_amount"):
			package["insured_amount"] = 0

		if not package.get("physical_packaging"):
			package["physical_packaging"] = "BOX"

		surcharge = surcharge + package.get("surcharge", 0)

	# check item conditions for applying Fedex One Rate pricing
	rate_settings = frappe.get_single("Shipment Rate Settings")
	RecipientCountryCode = get_country_code(to_address.get("country", ""))

	flat_rate = False
	signature_option = "DIRECT"
	packaging = packaging_type

	if RecipientCountryCode.lower() == "us":  # One Rate only applies for intra-US deliveries
		flat_rate_items = {item.item: item.max_qty for item in rate_settings.items}
		for item in items:
			if item.get("qty", 0) < flat_rate_items.get(item.get("item_code"), 0):
				flat_rate = True
				signature_option = None
				packaging = frappe.db.get_value("Shipment Rate Item Settings", {"item": item.get("item_code")}, "packaging")
				packaging = frappe.db.get_value("Shipping Package", packaging, "box_code")
			else:
				flat_rate = False
				signature_option = "DIRECT"
				packaging = packaging_type
				break

	# form rate request arguments
	rate_exceptions = []
	args = dict(
		DropoffType='REGULAR_PICKUP',
		PackagingType=packaging,
		EdtRequestType='NONE',
		PaymentType='SENDER',
		# Shipper
		ShipperPostalCode=(from_address.get("pincode") or "").strip(),
		ShipperCountryCode=get_country_code(from_address.get("country")),
		# Recipient
		RecipientPostalCode=(to_address.get("pincode") or "").strip(),
		IsResidential=to_address.get("is_residential"),
		RecipientCountryCode=RecipientCountryCode,
		# Delivery options
		package_list=packages,
		ignoreErrors=True,
		signature_option=signature_option,
		exceptions=rate_exceptions,
		delivery_date=doc.get("delivery_date", "") if doc else "",
		saturday_delivery=doc.get("saturday_delivery", "") if doc else "",
		flat_rate=flat_rate
	)

	if to_address:
		rates = get_fedex_packages_rate(**args) or []

		# since we're working on v18 of Fedex's rate service, which is incompatible with
		# getting One Rate and non-One Rate prices in the same query, we do another query
		# to get the non-One Rate prices and update the existing rates
		if flat_rate:
			non_flat_rate_args = args.copy()
			non_flat_rate_args.update({"flat_rate": False, "signature_option": "DIRECT", "PackagingType": packaging_type})
			flat_rates = get_fedex_packages_rate(**non_flat_rate_args) or []
			rates.extend(flat_rates)
	else:
		rates = []

	if rates:
		sorted_rates = []
		unique_labels = []
		for rate in sorted(rates, key=lambda rate: rate["fee"]):
			# remove duplicate shipping methods
			if rate["label"] in unique_labels:
				continue

			# disallow FEDEX GROUND for Canada
			if RecipientCountryCode.lower() == "ca" and rate['label'] == "FEDEX GROUND":
				continue

			unique_labels.append(rate["label"])
			rate["fee"] += surcharge

			if rate_settings.upcharge_type == "Percentage":
				rate["fee"] += (rate["fee"] * (rate_settings.upcharge / 100))
			elif rate_settings.upcharge_type == "Actual":
				rate["fee"] += rate_settings.upcharge

			rate['fee'] = round(rate['fee'], 2)
			sorted_rates.append(rate)

		return sorted_rates
	else:
		msg = "Could not get rates, please check your Shipping Address"
		if len(rate_exceptions) > 0:

			for ex in rate_exceptions:
				if ex["type"] == "request":
					msg = str(ex["exception"])
					break

		frappe.throw(msg, title="Error")
