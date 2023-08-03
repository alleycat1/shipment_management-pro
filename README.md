# 1. Shipment Management Overview

Shipment Management Process

# 2. License

The MIT License

Copyright (c) 2016 DigiThinkIt Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy of 
this software and associated documentation files (the "Software"), to deal in the 
Software without restriction, including without limitation the rights to use, copy, 
modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. 
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH 
THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# 3. Installation

## 3.1. Clone app from git

Go to folder:
```
cd frappe-bench
```

Execute command:
```
bench get-app shipment_management https://github.com/DigiThinkIT/shipment_management.git

```

## 3.2. Install app for your site
```
bench --site {site_name} install-app shipment_management
```

_Note: All sites are located in frappe-bench/sites folder_

##  3.3. Restart bench

On Dev:
```
bench start
```

On Production:
```
bench restart
```

## 3.4. Check that everything has been installed successful

New application is present in application list

```
bench list-apps
```

# 4. Uninstall/Remove


## 4.1. Uninstall
```
bench uninstall-app shipment_management
```

## 4.2. Remove

```
bench remove-from-installed-apps shipment_management
```

# 5.Config:
File _app-config_ is used for general shipment configuration. 

PRIMARY_FEDEX_DOC_NAME - Used to switch from Fedex Test Server to Fedex Production Server

# 6.DocTypes:

- DTI Shipment Note (Primary Doc Type)
- DTI Shipment Note Item (Items from Delivery Note, Table can be customised)
- DTI Shipment Package (Physical shipment box)
- DTI Fedex Shipment Configuration (Configuration DocType for Fedex Connection)

# 7. Supported Shipment Providers

## 7.1 FedEx

### Overview
FedEx Corporation is a US multinational courier delivery services company.
The company is known for its overnight shipping service, but also for pioneering a system 
that could track packages and provide real-time updates on package location.

# 8. Status Check Web Page
Added web page for customer to provide possibility to check status by tracking number

{site_path}\shipment_tracking.html

# 9. Automation Testing
Module was covered with functional testing. 

For run tests you should execute command:

```
bench run-tests --app shipment_management
```
or
```
bench run-tests --module "shipment_management.shipment_management.test_fedex"
```

# 10. Permissions
- Shipment Management Admin
- Shipment Management User

# 11. Debug
Log File:
_/home/frappe/frappe-bench/logs/frappe.log_

# 12. Report Creation
Report List -> New -> Save


# 13. API for shopping cart 
- get_fedex_packages_rate
- estimate_fedex_delivery_time
- get_carriers_list


# 14. Technical dept

1) Fedex status code are used - like PU, AA and etc.

It will be better to add some Fedex status mapper for show more user-friendly statuses like:
- At Airport 
- Plane Landed 
- At Delivery 
- In Progress

2) Real Delivery Note and Delivery Note Items are used in test - it will be better to create all tests data it tests.

3) We should remove TEMP-FEDEX Folder from our source code and import from fedex in python libs after Pull Request will be merged - https://github.com/python-fedex-devs/python-fedex/pull/84

4) RATE (provider_fedex.py)
We should remove YOUR_PACKAGING and use real PackagingType from doc, investigate error: Service is not allowed. (Code = 868)