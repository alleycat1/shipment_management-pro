# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "shipment_management"
app_title = "Shipment Management"
app_publisher = "DigiThinkit Inc."
app_description = "Shipment Application Management"
app_icon = "octicon octicon-file-directory"
app_color = "#FF8000"
app_email = "romanchuk.katerina@gmail.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/shipment_management/css/shipment_management.css"
doctype_js = {
    "Quotation": "public/js/get_rates.js",
    "Sales Invoice": "public/js/get_rates.js",
    "Sales Order": ["public/js/get_rates.js", "public/js/sales_order.js"],
    "Delivery Note": "public/js/custom_script.js"
}
doctype_list_js = {
    "Delivery Note": "public/js/custom_list.js"
}

# include js, css files in header of web template
# web_include_css = "/assets/shipment_management/css/style.css"
# web_include_js = "/assets/shipment_management/js/shipment_management.js"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "shipment_management.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "shipment_management.install.before_install"
after_install = "shipment_management.shipment.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "shipment_management.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
    "daily_long": ["shipment_management.shipment.shipment_status_update_controller"]}

# Testing
# -------

# before_tests = "shipment_management.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "shipment_management.event.get_events"
# }

shipping_rate_api = [
    {"name": "FedEx", "module": "shipment_management.api.get_rates"}
]

override_doctype_dashboards = {
    "Delivery Note": "shipment_management.utils.get_dn_dashboard_data",
    "Warranty Claim": "shipment_management.utils.get_wc_dashboard_data"
}
