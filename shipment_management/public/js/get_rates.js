frappe.ui.form.on("Quotation", {
	refresh: function(frm) {
		add_fedex_rates_button(frm);
	},

	get_fedex_rates: function(frm) {
		_get_fedex_rates(frm);
	}
});

frappe.ui.form.on("Sales Order", {
	refresh: function(frm) {
		add_fedex_rates_button(frm);
	},

	get_fedex_rates: function(frm) {
		_get_fedex_rates(frm);
	}
});

frappe.ui.form.on("Sales Invoice", {
	refresh: function(frm) {
		add_fedex_rates_button(frm);
	},

	get_fedex_rates: function(frm) {
		_get_fedex_rates(frm);
	}
});


function add_fedex_rates_button(frm) {
	if (frm.doc.docstatus == 0) {
		frm.add_custom_button(__('Get Fedex Rates'), function() {
			_get_fedex_rates(frm);
		});
	}
}

function _get_fedex_rates(frm) {
	frm.doc.taxes.forEach((item) => {
		if (item.account_head == "Freight and Forwarding Charges - JA") {
			frappe.throw("Shipment Charge has already been added");
		}
	})

	frappe.call({
		freeze: 1,
		method: 'shipment_management.shipengine.api.get_rates',
		args: {
			doc: frm.doc,
			estimate: true
		},
		callback: function(response) {
			let options = [];
			let service_dict = [];

			// form all the available shipping options
			$.each(response.message, function(index, value) {
				let estimated_arrival = isNaN(value.estimated_arrival) ? `(${value.estimated_arrival})` : `(${value.days} days)`;
				let option = `${value.label} - $${value.fee} ${estimated_arrival}`;

				options.push(option);
				service_dict.push({
					"label": option,
					"name": value.name,
					"fee": value.fee,
					"days": value.days,
					"arrival": value.estimated_arrival
				});
			});

			options.push("Pick Up - $0");
			service_dict.push({
				"label": "Pick Up - $0",
				"name": "pick_up",
				"fee": 0,
				"days": null,
				"arrival": null
			});

			// display all the shipping options
			frappe.prompt({
				"label": "Service Types",
				"fieldtype": "Select",
				"fieldname": "service_types",
				"options": options,
				"reqd": 1
			},
			function(data) {
				let selected_service = data.service_types;
				let service_data = service_dict.find((rate) => rate.label == selected_service);

				if (service_data.fee != 0) {
					frm.add_child("taxes", {
						"charge_type": "Actual",
						"account_head": "Freight and Forwarding Charges - JA",
						"tax_amount": service_data.fee,
						"description": `Shipping (${service_data.label}")`
					});
				};

				frm.set_value("fedex_shipping_method", service_data.name);
				refresh_field("taxes");
				frm.save();
			}, "Select Service");
		}
	})
}