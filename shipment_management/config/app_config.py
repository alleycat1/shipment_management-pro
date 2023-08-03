
class SupportedProviderList(object):
    Fedex = 'FEDEX'


PRIMARY_FEDEX_DOC_NAME = "Fedex Test Server Config"

# WTF? Move this to site_config / DB 
class FedexTestServerConfiguration(object):
    key = '0uSKxCgw6AZANfZ5'
    password = 'WFDeuKsHwGuplTgd7ESLK0FpB'
    account_number = '510087283'
    meter_number = '118747441'
    freight_account_number = '510087020'
    use_test_server = True


SHORT_COMPANY_NAME = """JH Audio"""


##################################################################

class FedexStatusCode(object):
    def __init__(self, status_code, definition):
        self.status_code = status_code
        self.definition = definition


class StatusMapFedexAndShipmentNote(object):
    """
    ALL STATUSES:
    AA - At Airport
    PL - Plane Landed
    AD - At Delivery
    PM - In Progress
    AF - At FedEx Facility
    PU - Picked Up
    AP - At Pickup
    PX - Picked up (see Details)
    AR - Arrived at
    RR - CDO Requested
    AX - At USPS facility
    RM - CDO Modified
    CA - Shipment Canceled
    RC - CDO Cancelled
    CH - Location Changed
    RS - Return to Shipper
    DD - Delivery Delay
    DE - Delivery Exception
    DL - Delivered
    DP - Departed FedEx Location
    SE - Shipment Exception
    DS - Vehicle dispatched
    SF - At Sort Facility
    DY - Delay
    EA - Enroute to Airport delay
    TR - Transfer
    """
    Completed = [FedexStatusCode("DL", "Delivered")]

    Canceled = [FedexStatusCode("CA", "Shipment Canceled")]

    Failed = [FedexStatusCode("DE", "Delivery Exception"),
              FedexStatusCode("SE", "Shipment Exception"),
              FedexStatusCode("RS", "Return to Shipper")]

##################################################################

ExportComplianceStatement = "NO EEI 30.37 (f)"
