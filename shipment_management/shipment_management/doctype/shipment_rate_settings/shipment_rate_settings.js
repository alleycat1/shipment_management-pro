// Copyright (c) 2016, DigiThinkit Inc. and contributors
// For license information, please see license.txt

/* global frappe */

const fedex_one_rate_packaging = [
	"FEDEX_SMALL_BOX", "FEDEX_MEDIUM_BOX", "FEDEX_LARGE_BOX",
	"FEDEX_EXTRA_LARGE_BOX", "FEDEX_PAK", "FEDEX_TUBE", "FEDEX_ENVELOPE"
];

frappe.ui.form.on("Shipment Rate Settings", {
	refresh: (frm) => {
		frm.set_query("packaging", "items", (doc, cdt, cdn) => {
			return { filters: { "box_code": ["IN", fedex_one_rate_packaging] } };
		});
	}
});

frappe.ui.form.on("Shipment Rate Item Settings", {
	item: (frm, cdt, cdn) => {
		frm.add_fetch("item", "item_name", "item_name");
	},

	items_add: (frm, cdt, cdn) => {
		// copy the preferred packaging from the first row
		frm.script_manager.copy_from_first_row("items", frm.selected_doc, "packaging");
	}
});
