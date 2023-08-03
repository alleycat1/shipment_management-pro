import logging
import unittest
import datetime

from shipment_management.shipment import *
from shipment_management.provider_fedex import get_html_code_status_with_fedex_tracking_number, get_fedex_packages_rate, \
	estimate_fedex_delivery_time
from shipment_management.config.app_config import SupportedProviderList


class TestCaseFedexAPI(unittest.TestCase):
	def setUp(self):
		logger = logging.getLogger('fedex')
		ch = logging.StreamHandler()
		ch.setLevel(logging.ERROR)
		logger.setLevel(logging.ERROR)
		logger.addHandler(ch)

	def tests_tracking_number_validation(self):
		response = get_html_code_status_with_fedex_tracking_number(track_value="1111111111")
		self.assertNotIn("Authentication Failed", response)

	def tests_get_package_rate_for_one_package_domestic(self):

		response = get_fedex_packages_rate(international=False,
										DropoffType='REGULAR_PICKUP',
										ServiceType='FEDEX_GROUND',
										PackagingType='YOUR_PACKAGING',
										ShipperStateOrProvinceCode='SC',
										ShipperPostalCode='29631',
										ShipperCountryCode='US',
										RecipientStateOrProvinceCode='NC',
										RecipientPostalCode='27577',
										RecipientCountryCode='US',
										EdtRequestType='NONE',
										PaymentType='SENDER',
										single_rate=True,
										package_list=[{'weight_value': 1.0,
												'weight_units': "LB",
												'physical_packaging': 'BOX',
												'group_package_count': 1,
												'insured_amount': 100}])

		self.assertEqual(response['fee'], 10.79)
		self.assertEqual(response['name'], "FEDEX_GROUND")

	def tests_get_package_rate_for_two_packages_domestic(self):

		response = get_fedex_packages_rate(international=False,
										DropoffType='REGULAR_PICKUP',
										ServiceType='FEDEX_GROUND',
										PackagingType='YOUR_PACKAGING',
										ShipperStateOrProvinceCode='SC',
										ShipperPostalCode='29631',
										ShipperCountryCode='US',
										RecipientStateOrProvinceCode='NC',
										RecipientPostalCode='27577',
										RecipientCountryCode='US',
										EdtRequestType='NONE',
										PaymentType='SENDER',
										single_rate=True,
										package_list=[{'weight_value': 1.0,
												'weight_units': "LB",
												'physical_packaging': 'BOX',
												'group_package_count': 1,
												'insured_amount': 200},
												  {'weight_value': 1.0,
												'weight_units': "LB",
												'physical_packaging': 'BOX',
												'group_package_count': 1,
												'insured_amount': 100}])

		self.assertEqual(response['fee'], 24.58)
		self.assertEqual(response['name'], "FEDEX_GROUND")

	def tests_get_package_rate_for_one_package_international(self):

		response = get_fedex_packages_rate(international=True,
										DropoffType='REGULAR_PICKUP',
										ServiceType='INTERNATIONAL_ECONOMY',
										PackagingType='YOUR_PACKAGING',
										ShipperStateOrProvinceCode='SC',
										ShipperPostalCode='29631',
										ShipperCountryCode='US',
										RecipientStateOrProvinceCode='',
										RecipientPostalCode='02140',
										RecipientCountryCode='UA',
										EdtRequestType='NONE',
										PaymentType='SENDER',
										single_rate=True,
										package_list=[{'weight_value': 1.0,
												'weight_units': "LB",
												'physical_packaging': 'BOX',
												'group_package_count': 1,
												'insured_amount': 100}])

		self.assertEqual(response['fee'], 102.4)
		self.assertEqual(response['name'], "INTERNATIONAL_ECONOMY")

	def tests_get_package_rate_for_two_packages_international(self):

		response = get_fedex_packages_rate(international=True,
										DropoffType='REGULAR_PICKUP',
										ServiceType='INTERNATIONAL_ECONOMY',
										PackagingType='YOUR_PACKAGING',
										ShipperStateOrProvinceCode='SC',
										ShipperPostalCode='29631',
										ShipperCountryCode='US',
										RecipientStateOrProvinceCode='',
										RecipientPostalCode='02140',
										RecipientCountryCode='UA',
										EdtRequestType='NONE',
										PaymentType='SENDER',
										single_rate=True,
										package_list=[{'weight_value': 1.0,
												'weight_units': "LB",
												'physical_packaging': 'BOX',
												'group_package_count': 1,
												'insured_amount': 200},
												  {'weight_value': 1.0,
												'weight_units': "LB",
												'physical_packaging': 'BOX',
												'group_package_count': 1,
												'insured_amount': 100}])

		self.assertEqual(response['fee'], 133.99)
		self.assertEqual(response['name'], "INTERNATIONAL_ECONOMY")

	def tests_estimate_delivery_time(self):
		response = estimate_fedex_delivery_time(OriginPostalCode='M5V 3A4',
												OriginCountryCode='CA',
												DestinationPostalCode='27577',
												DestinationCountryCode='US')

		try:
			datetime.datetime.strptime(response, "%Y-%m-%d")
		except ValueError as err:
			self.fail("Invalid response!" % err)


class TestCaseGeneralAPI(unittest.TestCase):
	def tests_define_carriers_list(self):
		response = get_carriers_list()
		self.assertEqual(len(response), 1)
		self.assertEqual(response[0], SupportedProviderList.Fedex)
