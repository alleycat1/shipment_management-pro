from __future__ import unicode_literals

import unittest

import random
import string
import frappe
import logging

from frappe.utils.make_random import get_random

from shipment_management.provider_fedex import parse_items_in_box, get_item_by_item_code, delete_fedex_shipment


def generate_random_string(amount_of_symbols=50000):
	return ''.join(random.choice(string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in
				   range(amount_of_symbols))


def delete_from_db(doc_type_table, key, value):
	frappe.db.sql('DELETE from `%s` WHERE %s="%s"' % (doc_type_table, key, value))


def get_count_from_db(table_name):
	return frappe.db.sql('SELECT COUNT(*) FROM `%s`' % table_name)[0][0]


def _print_debug_message():
	print("=" * 70)
	print("Amount of Delivery Note             = ", get_count_from_db('tabDelivery Note'))
	print("Amount of DTI Shipment Note         = ", get_count_from_db('tabDTI Shipment Note'))
	print("Amount of DTI Shipment Note Item    = ", get_count_from_db('tabDTI Shipment Note Item'))
	print("Amount of DTI Shipment Package      = ", get_count_from_db('tabDTI Shipment Package'))
	print("Amount of DTI Fedex Configuration   = ", get_count_from_db('tabDTI Fedex Configuration'))
	print("=" * 70)


def get_boxes(shipment_note_name):
	return frappe.db.sql('''SELECT * from `tabDTI Shipment Package` WHERE parent="%s"''' % shipment_note_name,
						 as_dict=True)


def get_attached_labels_count(tracking_number):
	response = frappe.db.sql(
		"""select file_url, file_name from tabFile WHERE file_name LIKE '%{}%'""".format(tracking_number),
		as_dict=True)
	return len(response)


def get_delivery_note(amount_of_items):
	# TODO Create delivery note with item in test
	delivery_note = get_random("Delivery Note")
	all_delivery_items = frappe.db.sql('''SELECT * from `tabDelivery Note Item`''', as_dict=True)

	items_list = []
	for i in xrange(1000):
		if all_delivery_items[i].item_code not in [item.item_code for item in items_list]:
			items_list.append(all_delivery_items[i])
			if len(items_list) == amount_of_items:
				break

	assert items_list, "Delivery Note Items are absent for testing"

	return delivery_note, items_list


###########################################################################
###########################################################################
###########################################################################

def setUpModule():
	print("\nBefore test execution:")
	_print_debug_message()

	# -------------------------------
	logger = logging.getLogger('fedex')
	ch = logging.StreamHandler()
	ch.setLevel(logging.ERROR)
	logger.setLevel(logging.ERROR)
	logger.addHandler(ch)


def tearDownModule():
	print("\nAfter test execution (and clean up):")

	frappe.clear_cache()
	_print_debug_message()


###########################################################################
###########################################################################
###########################################################################

class TestDocTypes(unittest.TestCase):
	def test_fedex_configuration(self):
		fedex_config = frappe.new_doc("DTI Fedex Configuration")

		fedex_config.fedex_config_name = "TestFedexName"
		fedex_config.fedex_key = "TestKey"
		fedex_config.password = "TestPassword"
		fedex_config.account_number = "TestAccountNumber"
		fedex_config.meter_number = "TestMeterNumber"
		fedex_config.freight_account_number = "FreightAccountNumber"
		fedex_config.use_test_server = False

		fedex_config.save()

		delete_from_db(doc_type_table="tabDTI Fedex Configuration", key='name', value=fedex_config.fedex_config_name)


###########################################################################
###########################################################################
###########################################################################


class TestDataConfig(object):
	BigTestDataList = [
		{'custom_value': 3,
		 'insurance': 1,
		 'quantity': 5,
		 'weight_value': 0.1,
		 'weight_units': 'LB'},
		{'custom_value': 5,
		 'insurance': 3,
		 'quantity': 5,
		 'weight_value': 1,
		 'weight_units': 'LB'},
		{'custom_value': 3,
		 'insurance': 1,
		 'quantity': 5,
		 'weight_value': 0.1,
		 'weight_units': 'LB'},
		{'custom_value': 5,
		 'insurance': 3,
		 'quantity': 5,
		 'weight_value': 1,
		 'weight_units': 'LB'},
		{'custom_value': 0.5,
		 'insurance': 0.3,
		 'quantity': 5,
		 'weight_value': 1,
		 'weight_units': 'LB'},
		{'custom_value': 6,
		 'insurance': 4,
		 'quantity': 4,
		 'weight_value': 0.1,
		 'weight_units': 'LB'},
		{'custom_value': 10,
		 'insurance': 9,
		 'quantity': 4,
		 'weight_value': 0.1,
		 'weight_units': 'LB'},
		{'custom_value': 5,
		 'insurance': 3,
		 'quantity': 5,
		 'weight_value': 0.3,
		 'weight_units': 'LB'},
		{'custom_value': 10,
		 'insurance': 9,
		 'quantity': 4,
		 'weight_value': 0.2,
		 'weight_units': 'LB'}]

	ExportTestDataDetailMaxValue=[{'custom_value': 2501,
								   'insurance': 2501,
								   'quantity': 1,
								   'weight_value': 1,
								   'weight_units': 'LB'}]

	InsuranceZeroForAllItems = [
					{'custom_value': 3,
					 'insurance': 0,
					 'quantity': 5,
					 'weight_value': 0.1,
					 'weight_units': 'LB'},
					{'custom_value': 5,
					 'insurance': 0,
					 'quantity': 5,
					 'weight_value': 1,
					 'weight_units': 'LB'},
					{'custom_value': 3,
					 'insurance': 0,
					 'quantity': 5,
					 'weight_value': 0.1,
					 'weight_units': 'LB'},
					{'custom_value': 5,
					 'insurance': 0,
					 'quantity': 5,
					 'weight_value': 1,
					 'weight_units': 'LB'},
					{'custom_value': 0.5,
					 'insurance': 0,
					 'quantity': 5,
					 'weight_value': 1,
					 'weight_units': 'LB'},
					{'custom_value': 6,
					 'insurance': 0,
					 'quantity': 4,
					 'weight_value': 0.1,
					 'weight_units': 'LB'},
					{'custom_value': 10,
					 'insurance': 0,
					 'quantity': 4,
					 'weight_value': 0.1,
					 'weight_units': 'LB'},
					{'custom_value': 5,
					 'insurance': 0,
					 'quantity': 5,
					 'weight_value': 0.3,
					 'weight_units': 'LB'},
					{'custom_value': 10,
					 'insurance': 0,
					 'quantity': 4,
					 'weight_value': 0.2,
					 'weight_units': 'LB'}]

	InsuranceZeroForPartItems = [
				{'custom_value': 3,
				 'insurance': 0.4,
				 'quantity': 5,
				 'weight_value': 0.1,
				 'weight_units': 'LB'},
				{'custom_value': 5,
				 'insurance': 0,
				 'quantity': 5,
				 'weight_value': 1,
				 'weight_units': 'LB'},
				{'custom_value': 3,
				 'insurance': 0,
				 'quantity': 5,
				 'weight_value': 0.1,
				 'weight_units': 'LB'},
				{'custom_value': 5,
				 'insurance': 0,
				 'quantity': 5,
				 'weight_value': 1,
				 'weight_units': 'LB'},
				{'custom_value': 0.5,
				 'insurance': 0,
				 'quantity': 5,
				 'weight_value': 1,
				 'weight_units': 'LB'},
				{'custom_value': 6,
				 'insurance': 1,
				 'quantity': 4,
				 'weight_value': 0.1,
				 'weight_units': 'LB'},
				{'custom_value': 10,
				 'insurance': 0,
				 'quantity': 4,
				 'weight_value': 0.1,
				 'weight_units': 'LB'},
				{'custom_value': 5,
				 'insurance': 0,
				 'quantity': 5,
				 'weight_value': 0.3,
				 'weight_units': 'LB'},
				{'custom_value': 10,
				 'insurance': 5,
				 'quantity': 4,
				 'weight_value': 0.2,
				 'weight_units': 'LB'}]

###########################################################################


class TestShipmentBase(unittest.TestCase):
	def setUp(self):
		self.note_list = []

	def tearDown(self):
		for note in self.note_list:
			if self.note.tracking_number not in ("0000-0000-0000-0000", "1111111111"):
				delete_fedex_shipment(note)

			delete_from_db(doc_type_table="tabDTI Shipment Note", key='name', value=note.name)
			delete_from_db(doc_type_table="tabDTI Shipment Note Item", key='parent', value=note.name)
			delete_from_db(doc_type_table="tabDTI Shipment Package", key='parent', value=note.name)

	def get_saved_shipment_note(self, international_shipment=False, test_data_for_items=[]):

		self.note = frappe.new_doc("DTI Shipment Note")

		delivery_note, items = get_delivery_note(amount_of_items=len(test_data_for_items))

		for i, item in enumerate(items):
			if international_shipment:
				item.custom_value = test_data_for_items[i]['custom_value']

			item.insurance = test_data_for_items[i]['insurance']
			item.qty = test_data_for_items[i]['quantity']
			item.weight_value = test_data_for_items[i]['weight_value']
			item.weight_units = test_data_for_items[i]['weight_units']

		if international_shipment:
			self.note.update({"delivery_note": delivery_note,
							  "international_shipment": True,
							  "service_type_international": "INTERNATIONAL_ECONOMY",
							  "recipient_contact_person_name": "Retty Geropter",
							  "recipient_company_name": "Sony Corporation",
							  "recipient_contact_phone_number": "676786786876",
							  "recipient_address_street_lines": "Lesi Ukrainki 23 fl 34",
							  "recipient_address_city": "Kiev",
							  "recipient_address_state_or_province_code": "",
							  "recipient_address_country_code": "UA",
							  "recipient_address_postal_code": "02140",
							  "contact_email": "1234567@gmail.com",
							  "shipper_contact_person_name": "Bora Bora",
							  "shipper_company_name": "Katerina",
							  "shipper_contact_phone_number": "12345678",
							  "shipper_address_street_lines": "Street 123456",
							  "shipper_address_city": "Herndon",
							  "shipper_address_state_or_province_code": "VA",
							  "shipper_address_country_code": "US",
							  "shipper_address_postal_code": "20192",
							  "delivery_items": items,
							  })

		else:
			self.note.update({"delivery_note": delivery_note,
							  "international_shipment": False,
							  "service_type_domestic": "FEDEX_2_DAY",
							  "recipient_contact_person_name": "George",
							  "recipient_company_name": "Fantastic Book shop",
							  "recipient_contact_phone_number": "0234876",
							  "recipient_address_street_lines": "b/t 24th St & 23rd St Potrero Hill",
							  "recipient_address_city": "Minnesota",
							  "recipient_address_state_or_province_code": "MN",
							  "recipient_address_country_code": "US",
							  "recipient_address_postal_code": "55037",
							  "contact_email": "shop@gmail.com",
							  "shipper_contact_person_name": "Terry Gihtrer-Assew",
							  "shipper_company_name": "JH Audio Company",
							  "shipper_contact_phone_number": "12345678",
							  "shipper_address_street_lines": "St & 230rd St Terropty Hill",
							  "shipper_address_city": "Florida",
							  "shipper_address_state_or_province_code": "FL",
							  "shipper_address_country_code": "US",
							  "shipper_address_postal_code": "32216",
							  "delivery_items": items,
							  })

		self.note.save()
		print("-" * 45)
		print("      [ %s ] " % self.note.name)
		print("-" * 45)

		self.note_list.append(self.note)

	def submit_and_validate(self):
		self.assertEqual(self.note.tracking_number, "0000-0000-0000-0000")
		self.assertIsNone(self.note.label_1)

		self.note.submit()

		self.assertNotEqual(self.note.tracking_number, "0000-0000-0000-0000")

	def validate_error_during_shipment_creation(self, expected_error_message):
		print("EXPECTED ERROR:", expected_error_message)
		try:
			self.submit_and_validate()
			self.fail("Shipment was created successful with wrong data")
		except frappe.ValidationError as error:
			if expected_error_message not in str(error):
				self.fail("Wrong expected error: %s" % error)

	def add_to_box(self, physical_packaging="BOX", items_to_ship_in_one_box=[]):
		text = "\n".join(r"{}:{}".format(item.item_code, int(item.qty)) for item in items_to_ship_in_one_box)

		print("\nAdded to the box:")
		print(text)

		self.note.append("box_list", {"physical_packaging": physical_packaging,
									  "packaging_type": "Fedex Small Box",
									  "items_in_box": text,
									  "tracking_number" : "1111111111"})
		self.note.save()

# ##########################################################################
# ##########################################################################


class TestCaseDomestic(TestShipmentBase):

	def test_all_in_one_box(self):
		self.get_saved_shipment_note(test_data_for_items=TestDataConfig.BigTestDataList)

		self.add_to_box(items_to_ship_in_one_box=self.note.delivery_items)

		self.submit_and_validate()

	def test_all_in_different_boxes(self):
		self.get_saved_shipment_note(test_data_for_items=TestDataConfig.BigTestDataList)

		for i in xrange(len(TestDataConfig.BigTestDataList)):
			self.add_to_box(items_to_ship_in_one_box=[self.note.delivery_items[i]])

		self.submit_and_validate()

	def test_export_detail(self):
		self.get_saved_shipment_note(test_data_for_items=TestDataConfig.ExportTestDataDetailMaxValue)

		self.add_to_box(items_to_ship_in_one_box=self.note.delivery_items)

		self.submit_and_validate()

	def test_insurance_zero_1(self):
		self.get_saved_shipment_note(test_data_for_items=TestDataConfig.InsuranceZeroForAllItems)

		self.add_to_box(items_to_ship_in_one_box=self.note.delivery_items)

		self.submit_and_validate()

	def test_insurance_zero_2(self):
		self.get_saved_shipment_note(test_data_for_items=TestDataConfig.InsuranceZeroForAllItems)

		for i in xrange(len(TestDataConfig.InsuranceZeroForAllItems)):
			self.add_to_box(items_to_ship_in_one_box=[self.note.delivery_items[i]])

		self.submit_and_validate()

	def test_insurance_zero_3(self):
		self.get_saved_shipment_note(test_data_for_items=TestDataConfig.InsuranceZeroForPartItems)

		self.add_to_box(items_to_ship_in_one_box=self.note.delivery_items)

		self.submit_and_validate()

	def test_insurance_zero_4(self):
		self.get_saved_shipment_note(test_data_for_items=TestDataConfig.InsuranceZeroForPartItems)

		for i in xrange(len(TestDataConfig.InsuranceZeroForPartItems)):
			self.add_to_box(items_to_ship_in_one_box=[self.note.delivery_items[i]])

		self.submit_and_validate()

# ##########################################################################
# ##########################################################################

## Disabled International Shipment Tests


# class TestCaseInternational(TestShipmentBase):
# 	def test_all_in_one_box(self):
# 		self.get_saved_shipment_note(international_shipment=True,
# 									 test_data_for_items=TestDataConfig.BigTestDataList)

# 		self.add_to_box(items_to_ship_in_one_box=self.note.delivery_items)

# 		self.submit_and_validate()

# 	def test_all_in_different_boxes_1(self):
# 		self.get_saved_shipment_note(international_shipment=True,
# 										test_data_for_items=TestDataConfig.BigTestDataList)

# 		for i in xrange(len(TestDataConfig.BigTestDataList)):
# 			self.add_to_box(items_to_ship_in_one_box=[self.note.delivery_items[i]])

# 		self.submit_and_validate()

# 	def test_all_in_different_boxes_2(self):
# 		self.get_saved_shipment_note(international_shipment=True,
# 									 test_data_for_items=TestDataConfig.BigTestDataList)

# 		self.add_to_box(items_to_ship_in_one_box=self.note.delivery_items[1:3])
# 		self.add_to_box(items_to_ship_in_one_box=self.note.delivery_items[3:4])
# 		self.add_to_box(items_to_ship_in_one_box=self.note.delivery_items[5:9])

# 		self.submit_and_validate()

# 	def test_all_in_different_boxes_3(self):
# 		self.get_saved_shipment_note(international_shipment=True,
# 									 test_data_for_items=TestDataConfig.BigTestDataList)

# 		self.add_to_box(items_to_ship_in_one_box=self.note.delivery_items[1:3])
# 		self.add_to_box(items_to_ship_in_one_box=self.note.delivery_items[5:9])

# 		self.submit_and_validate()

# 	def test_export_detail(self):
# 		self.get_saved_shipment_note(international_shipment=True,
# 									 test_data_for_items=TestDataConfig.ExportTestDataDetailMaxValue)

# 		self.add_to_box(items_to_ship_in_one_box=self.note.delivery_items)

# 		self.submit_and_validate()

# 	def test_insurance_and_custom_value(self):
# 		self.get_saved_shipment_note(international_shipment=True,
# 									 test_data_for_items=[{'custom_value': 2,
# 														 'insurance': 1000,
# 														 'quantity': 5,
# 														 'weight_value': 1,
# 														 'weight_units': 'LB'
# 														 }])

# 		self.add_to_box(items_to_ship_in_one_box=self.note.delivery_items)

# 		self.validate_error_during_shipment_creation(expected_error_message=
# 													 "Total Insured value exceeds customs value (Error code: 2519)")

# 	def test_insurance_and_custom_value_2(self):
# 		self.get_saved_shipment_note(international_shipment=True,
# 									 test_data_for_items=[{'custom_value': 0,
# 														 'insurance': 1,
# 														 'quantity': 5,
# 														 'weight_value': 1,
# 														 'weight_units': 'LB'
# 														 }])

# 		self.add_to_box(items_to_ship_in_one_box=self.note.delivery_items)

# 		self.validate_error_during_shipment_creation(expected_error_message=
# 													 "CUSTOM VALUE = 0")

# 	def test_insurance_zero_1(self):
# 		self.get_saved_shipment_note(international_shipment=True,
# 									 test_data_for_items=TestDataConfig.InsuranceZeroForAllItems)

# 		self.add_to_box(items_to_ship_in_one_box=self.note.delivery_items)

# 		self.submit_and_validate()

# 	def test_insurance_zero_2(self):
# 		self.get_saved_shipment_note(international_shipment=True,
# 									 test_data_for_items=TestDataConfig.InsuranceZeroForAllItems)

# 		for i in xrange(len(TestDataConfig.InsuranceZeroForAllItems)):
# 			self.add_to_box(items_to_ship_in_one_box=[self.note.delivery_items[i]])

# 		self.submit_and_validate()

# 	def test_insurance_zero_3(self):
# 		self.get_saved_shipment_note(international_shipment=True,
# 									 test_data_for_items=TestDataConfig.InsuranceZeroForPartItems)

# 		self.add_to_box(items_to_ship_in_one_box=self.note.delivery_items)

# 		self.submit_and_validate()

# 	def test_insurance_zero_4(self):
# 		self.get_saved_shipment_note(international_shipment=True,
# 									 test_data_for_items=TestDataConfig.InsuranceZeroForPartItems)

# 		for i in xrange(len(TestDataConfig.InsuranceZeroForPartItems)):
# 			self.add_to_box(items_to_ship_in_one_box=[self.note.delivery_items[i]])

# 		self.submit_and_validate()

if __name__ == '__main__':
	unittest.main()
