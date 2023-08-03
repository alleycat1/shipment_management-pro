from __future__ import unicode_literals
import frappe
import traceback


def get_context(context):
	try:
		doc_name = frappe.request.args.get('name', '')

		doc = frappe.get_doc('DTI Shipment Note', doc_name)

		context.no_cache = 1
		context.no_sitemap = 1

		context['label_url_1'] = doc.label_1
		context['label_url_2'] = doc.label_2
		context['label_url_3'] = doc.label_3
		context['label_url_4'] = doc.label_4
		context['label_url_5'] = doc.label_5
		context['label_url_6'] = doc.label_6
		context['label_url_7'] = doc.label_7
		context['label_url_8'] = doc.label_8
		context['label_url_9'] = doc.label_9
		context['label_url_10'] = doc.label_10

	except Exception:

		print(traceback.format_exc())