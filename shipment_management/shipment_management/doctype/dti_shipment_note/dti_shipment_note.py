# -*- coding: utf-8 -*-
# Copyright (c) 2015, DigiThinkit Inc. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.file_manager import *
from frappe.utils import cstr


class DTIShipmentNote(Document):

	def validate(self):
		if self.service_type_domestic == "PICK_UP" or self.service_type_international == "PICK_UP":
			frappe.throw(_("Shipment service type cannot be PICK UP!"))

		if not self.sales_order and self.delivery_items:
			self.sales_order = self.delivery_items[0].against_sales_order

		if not self.sales_order_date:
			self.sales_order_date = frappe.db.get_value("Sales Order", self.sales_order, "transaction_date")

	def set_tracking_ids(self):
		updated_tracking_ids = ""
		tracking_ids = ",".join([box.tracking_number.replace("-", "") for box in self.box_list])

		for so in set([item.against_sales_order for item in self.delivery_items]):
			existing_tracking_ids = frappe.db.get_value("Sales Order", so, "tracking_ids")
			if existing_tracking_ids:
				if not tracking_ids in existing_tracking_ids:
					updated_tracking_ids = existing_tracking_ids + "," + tracking_ids
			else:
				updated_tracking_ids = tracking_ids

			frappe.db.set_value("Sales Order", so, "tracking_ids", updated_tracking_ids)

	def on_submit(self):
		from shipment_management.shipment import ShipmentNoteOperationalStatus
		# from shipment_management.config.app_config import SupportedProviderList

		# if self.shipment_provider != SupportedProviderList.Fedex:
		# 	frappe.throw(_("Please specify shipment provider!"))

		# if self.shipment_provider == SupportedProviderList.Fedex:
		# 	from shipment_management.provider_fedex import create_fedex_shipment
		# 	create_fedex_shipment(self)

		for box in self.box_list:
			if not box.tracking_number:
				frappe.throw("Please enter Tracking No for BOX " + str(box.idx))

		self.set_tracking_ids()

		frappe.db.set(self, 'fedex_status', ShipmentNoteOperationalStatus.InProgress)
		if self.box_list and self.box_list[0].get("tracking_number"):
			frappe.db.set(self, 'tracking_number', self.box_list[0].tracking_number)

	def on_cancel(self):
		tracking_ids_list = frappe.db.get_value("Sales Order", self.sales_order, "tracking_ids").split(',')

		for box in self.box_list:
			if box.tracking_number in tracking_ids_list:
				tracking_ids_list.remove(box.tracking_number)

		frappe.db.set_value("Sales Order", self.sales_order, "tracking_ids", ','.join(map(str, tracking_ids_list)))

		# from shipment_management.config.app_config import SupportedProviderList
		# from shipment_management.shipment import ShipmentNoteOperationalStatus

		# if self.shipment_provider == SupportedProviderList.Fedex:

		# 	try:
		# 		from shipment_management.provider_fedex import delete_fedex_shipment
		# 		delete_fedex_shipment(self)
		# 		frappe.msgprint(_("Shipment {} has been canceled!".format(self.name)))

		# 		frappe.db.set(self, 'fedex_status', ShipmentNoteOperationalStatus.Cancelled)
		# 	except Exception, error:
		# 		frappe.throw(_(error))
