# -*- coding: utf-8 -*-
# Copyright (c) 2015, DigiThinkit Inc. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint
from frappe.model.document import Document

class ShippingPackageRule(Document):
	pass

def find_packages(items):
	"""This method iterates over all items passed finding rules for these items,
	then iterates over the rule items to find a package for the qty passed.

	It then uses this package rule to creates a fedex package def dictionary that
	can be used to fetch rate information.

	This method is very simple and doesn't account for organizing multiple different
	items in boxes or figuring out what fits best."""

	packages = []

	for item in items:
		product = frappe.get_all("Item", fields=["name", "net_weight"], filters={"item_code": item.get("item_code")})
		if product and len(product) > 0:
			product = product[0]
			package_rule_items = frappe.get_all("Shipping Package Rule Item", fields=["*"], filters={"parent": product.get("name")})
			parent_rule = None
			rule = None
			package_def = None
			if package_rule_items and len(package_rule_items) > 0:
				parent_rule = frappe.get_doc("Shipping Package Rule", product.get("name"))
				for rule_item in package_rule_items:
					if rule_item.get("qty") <= item.get("qty", 1):
						rule = rule_item
						package_def = frappe.get_doc("Shipping Package", rule.get("package"))

			weight = product.get("net_weight", 1)
			if weight < 1:
				weight = 1

			if rule:

				insurance_amount = parent_rule.get("insurance_amount", 0)
				if parent_rule.get("insurace_multiply"):
					insurance_amount = insurance_amount * item.get("qty", 1)

				packages.append({
					"weight_value": cint(weight * item.get("qty", 1)),
					"weight_units": "LB",
					"physical_packaging": "BOX",
					"dimensions": {
						"length": package_def.get("length"),
						"width": package_def.get("width"),
						"height": package_def.get("height"),
						"units": "IN"
					},
					"surcharge": rule.get("surcharge", 0),
					"group_package_count": item.get("qty", 1),
					"insured_amount": insurance_amount
				})
			else:
				packages.append({
					"weight_value": cint(weight * item.get("qty", 1)),
					"weight_units": "LB",
					"physical_packaging": "BOX",
					"group_package_count": item.get("qty", 1)
				})
	return packages
