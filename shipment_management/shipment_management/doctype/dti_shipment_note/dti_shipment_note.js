// Copyright (c) 2016, DigiThinkit Inc. and contributors
// For license information, please see license.txt

// --------------------------------------------------------------

const give_estimates = function (doc) {
    return frappe.call({
        freeze: 1,
        method: 'shipment_management.provider_fedex.show_shipment_estimates',
        args: {
            doc_name: doc.doc.name
        }
    })
};

// --------------------------------------------------------------

cur_frm.cscript.estimate = function () {
    cur_frm.save();
    setTimeout(function(){
        give_estimates(cur_frm)
    }, 1500)
}

// --------------------------------------------------------------

frappe.ui.form.on('DTI Shipment Note', {
    refresh: function (frm) {
        frm.set_query("packaging_type", "box_list", function(){
            return{
                query : "shipment_management.utils.get_packages_in_order"
            }
        })
        cur_frm.refresh_fields();
        $("[data-fieldname='international_shipment']").css({
            'text-transform': 'uppercase',
            'font-size': '16px'
        })
        $("[data-fieldname='estimate']:button").addClass('btn-primary')

        if (frm.doc.__islocal) {
            frm.set_value("total_insurance", "0")
            frm.set_value("total_custom_value", "0")
            frm.set_value("total_weight", "0")
        }


        if (cur_frm.doc.docstatus == 1) {
            if (cur_frm.doc.label_1) {
                cur_frm.add_custom_button(__('Print label'),
                    function () {
                        var url = '/labels?name=' + cur_frm.doc.name
                        window.open(url, "_blank")
                    }).addClass("btn btn-primary");
            }
            cur_frm.add_custom_button(__('Track Shipments'),
                    function () {
                        var tracking_nos = ""
                        for(var i =0; i < cur_frm.doc.box_list.length; i++){
                            tracking_nos = tracking_nos + cur_frm.doc.box_list[i].tracking_number + ","
                        }
                        var url = "https://www.fedex.com/apps/fedextrack/?action=track&tracknumbers=" + tracking_nos + "&locale=en_US&cntry_code=us"
                        window.open(url, "_blank");
                    }).addClass("btn btn-primary");
            }

    },
    on_submit: function (frm) {
        cur_frm.reload_doc();
    }

});

// --------------------------------------------------------------

frappe.ui.form.on("DTI Shipment Package", "items_in_box", function (frm, _doctype, currentPackageName) {
    var currentPackage = getPackageByName(frm.doc.box_list, currentPackageName);
    if (currentPackage) {
        var processedInput = processItemsInTheBox(currentPackage.items_in_box);

        if (processedInput.invalidLines.length) {
            alert(__("WARNING! Bad lines:\n" + processedInput.invalidLines.join("\n")));
        }

        for (var i = 0; i < processedInput.items.length; i++)
            var curent_item_code_from_user = processedInput.items[i].itemCode

        var parsed_item = getItemByItemCode(frm.doc.delivery_items, curent_item_code_from_user)

        if (!!parsed_item) {
            show_alert(__("OK! Added to box: " + curent_item_code_from_user));
        }

        var currentValues = calculatePackageValues(frm.doc.delivery_items, processedInput.items);


        currentPackage.total_box_insurance = currentValues.insurance;
        currentPackage.total_box_custom_value = currentValues.customValue;
        currentPackage.total_box_weight = currentValues.weightValue;

        cur_frm.refresh_fields("total_box_insurance")
        cur_frm.refresh_fields("total_box_custom_value")
        cur_frm.refresh_fields("total_box_weight")


        for (var i = 0, global_insuarance = 0; i < frm.doc.box_list.length; global_insuarance += frm.doc.box_list[i++].total_box_insurance);
        for (var i = 0, global_custom_value = 0; i < frm.doc.box_list.length; global_custom_value += frm.doc.box_list[i++].total_box_custom_value);
        for (var i = 0, global_weight_value = 0; i < frm.doc.box_list.length; global_weight_value += frm.doc.box_list[i++].total_box_weight);

        frappe.model.set_value(currentPackage.parenttype, currentPackage.parent, 'total_insurance', global_insuarance);
        frappe.model.set_value(currentPackage.parenttype, currentPackage.parent, 'total_custom_value', global_custom_value);
        frappe.model.set_value(currentPackage.parenttype, currentPackage.parent, 'total_weight', global_weight_value);

    }

});

// --------------------------------------------------------------

function getPackageByName(packages, packageName) {
    for (var i = 0; i < packages.length; i++) {
        if (packages[i].name === packageName) {
            return packages[i];
        }
    }
}

function getItemByItemCode(items, itemCode) {
    for (var i = 0; i < items.length; i++) {
        if (items[i].item_code === itemCode) {
            return items[i];
        }
    }
}

function processItemsInTheBox(rawItems) {
    var result = {
        items: [],
        invalidLines: []
    };
    if (!rawItems || typeof (rawItems) !== "string") {
        return result;
    }

    var lines = rawItems.split('\n');
    for (var i = 0; i < lines.length; i++) {
        var parts = lines[i].split(':');
        switch (parts.length) {
            case 2:
                result.items.push({
                    itemCode: parts[0],
                    qty: parseInt(parts[1])
                });
                break;
            default:
                if (lines[i] !== '') {
                    result.invalidLines.push(lines[i]);
                }
                break;
        }
    }

    return result;
}

function calculatePackageValues(allItems, enteredItems) {
    var result = {
        insurance: 0,
        customValue: 0,
        weightValue: 0
    };
    for (var i = 0; i < enteredItems.length; i++) {
        var item = getItemByItemCode(allItems, enteredItems[i].itemCode);
        if (!!item) {

            result.insurance += item.insurance * enteredItems[i].qty;
            result.customValue += item.custom_value * enteredItems[i].qty;
            result.weightValue += item.weight_value * enteredItems[i].qty;
        }
    }
    return result;
}


// --------------------------------------------------------------

const get_recipient_info = function (doc) {
    return frappe.call({
        method: 'shipment_management.shipment.get_recipient_details',
        args: {
            delivery_note_name: cur_frm.doc.delivery_note
        }
    });
};


const get_shipper_info = function (doc) {
    return frappe.call({
        method: 'shipment_management.shipment.get_shipper_details',
        args: {
            delivery_note_name: cur_frm.doc.delivery_note
        }
    });
};

const get_delivery_items = function (doc) {
    return frappe.call({
        method: 'shipment_management.shipment.get_delivery_items',
        args: {
            delivery_note_name: cur_frm.doc.delivery_note
        }
    });
};

const get_sales_order = function (doc) {
    return frappe.call({
        method: 'shipment_management.shipment.get_sales_order',
        args: {
            delivery_note_name: cur_frm.doc.delivery_note
        }
    });
};

// --------------------------------------------------------------

cur_frm.fields_dict['delivery_note'].get_query = function (doc) {
    return {
        filters: {
            "docstatus": '1'
        }
    }
}


// --------------------------------------------------------------

frappe.ui.form.on('DTI Shipment Note', "delivery_note", function (frm) {
        if (frm.doc.delivery_note) {

            get_delivery_items()
                .done(function (item_list) {
                    frappe.model.clear_table(cur_frm.doc, 'delivery_items');
                    for (i = 0; i < item_list.message.length; i++) {

                        var new_row = frappe.model.add_child(cur_frm.doc, "DTI Shipment Note Item", "delivery_items")

                        var dt = "DTI Shipment Note Item";

                        frappe.model.set_value(dt, new_row.name, 'barcode', item_list.message[i].barcode);
                        frappe.model.set_value(dt, new_row.name, 'item_code', item_list.message[i].item_code);
                        frappe.model.set_value(dt, new_row.name, 'item_name', item_list.message[i].item_name);
                        frappe.model.set_value(dt, new_row.name, 'customer_item_code', item_list.message[i].customer_item_code);
                        frappe.model.set_value(dt, new_row.name, 'description', item_list.message[i].description);
                        frappe.model.set_value(dt, new_row.name, 'image', item_list.message[i].image);
                        frappe.model.set_value(dt, new_row.name, 'image_view', item_list.message[i].image_view);
                        frappe.model.set_value(dt, new_row.name, 'qty', item_list.message[i].qty);
                        frappe.model.set_value(dt, new_row.name, 'price_list_rate', item_list.message[i].price_list_rate);
                        frappe.model.set_value(dt, new_row.name, 'stock_uom', item_list.message[i].stock_uom);
                        frappe.model.set_value(dt, new_row.name, 'base_price_list_rate', item_list.message[i].base_price_list_rate);
                        frappe.model.set_value(dt, new_row.name, 'discount_percentage', item_list.message[i].discount_percentage);
                        frappe.model.set_value(dt, new_row.name, 'margin_rate_or_amount', item_list.message[i].margin_rate_or_amount);
                        frappe.model.set_value(dt, new_row.name, 'total_margin', item_list.message[i].total_margin);
                        frappe.model.set_value(dt, new_row.name, 'rate', item_list.message[i].rate);
                        frappe.model.set_value(dt, new_row.name, 'amount', item_list.message[i].amount);
                        frappe.model.set_value(dt, new_row.name, 'base_rate', item_list.message[i].base_rate);
                        frappe.model.set_value(dt, new_row.name, 'base_amount', item_list.message[i].base_amount);
                        frappe.model.set_value(dt, new_row.name, 'pricing_rule', item_list.message[i].pricing_rule);
                        frappe.model.set_value(dt, new_row.name, 'net_rate', item_list.message[i].net_rate);
                        frappe.model.set_value(dt, new_row.name, 'net_amount', item_list.message[i].net_amount);
                        frappe.model.set_value(dt, new_row.name, 'base_net_rate', item_list.message[i].base_net_rate);
                        frappe.model.set_value(dt, new_row.name, 'base_net_amount', item_list.message[i].base_net_amount);
                        frappe.model.set_value(dt, new_row.name, 'warehouse', item_list.message[i].warehouse);
                        frappe.model.set_value(dt, new_row.name, 'target_warehouse', item_list.message[i].target_warehouse);
                        frappe.model.set_value(dt, new_row.name, 'serial_no', item_list.message[i].serial_no);
                        frappe.model.set_value(dt, new_row.name, 'batch_no', item_list.message[i].batch_no);
                        frappe.model.set_value(dt, new_row.name, 'actual_qty', item_list.message[i].actual_qty);
                        frappe.model.set_value(dt, new_row.name, 'actual_batch_qty', item_list.message[i].actual_batch_qty);
                        frappe.model.set_value(dt, new_row.name, 'item_group', item_list.message[i].item_group);
                        frappe.model.set_value(dt, new_row.name, 'brand', item_list.message[i].brand);
                        frappe.model.set_value(dt, new_row.name, 'expense_account', item_list.message[i].expense_account);
                        frappe.model.set_value(dt, new_row.name, 'cost_center', item_list.message[i].cost_center);
                        frappe.model.set_value(dt, new_row.name, 'against_sales_order', item_list.message[i].against_sales_order);
                        frappe.model.set_value(dt, new_row.name, 'against_sales_invoice', item_list.message[i].against_sales_invoice);
                        frappe.model.set_value(dt, new_row.name, 'so_detail', item_list.message[i].so_detail);
                        frappe.model.set_value(dt, new_row.name, 'si_detail', item_list.message[i].si_detail);
                        frappe.model.set_value(dt, new_row.name, 'installed_qty', item_list.message[i].installed_qty);
                        frappe.model.set_value(dt, new_row.name, 'billed_amt', item_list.message[i].billed_amt);

                        cur_frm.refresh_fields("delivery_items")
                    }

                });
            get_recipient_info()
                .done(function (recipient) {
                    var resp = recipient.message
                    frappe.model.set_value('DTI Shipment Note', cur_frm.doc.name, 'recipient_contact_person_name', resp['recipient_contact_person_name']);
                    frappe.model.set_value('DTI Shipment Note', cur_frm.doc.name, 'recipient_company_name', resp['recipient_company_name']);
                    frappe.model.set_value('DTI Shipment Note', cur_frm.doc.name, 'recipient_contact_phone_number', resp['recipient_contact_phone_number']);
                    frappe.model.set_value('DTI Shipment Note', cur_frm.doc.name, 'recipient_address_street_lines', resp['recipient_address_street_lines']);
                    frappe.model.set_value('DTI Shipment Note', cur_frm.doc.name, 'recipient_address_city', resp['recipient_address_city']);
                    frappe.model.set_value('DTI Shipment Note', cur_frm.doc.name, 'recipient_address_state_or_province_code', resp['recipient_address_state_or_province_code']);
                    frappe.model.set_value('DTI Shipment Note', cur_frm.doc.name, 'recipient_address_country_code', resp['recipient_address_country_code']);
                    frappe.model.set_value('DTI Shipment Note', cur_frm.doc.name, 'recipient_address_postal_code', resp['recipient_address_postal_code']);

                    frappe.model.set_value('DTI Shipment Note', cur_frm.doc.name, 'contact_email', resp['contact_email']);


                });

            get_shipper_info()
                .done(function (shipper) {
                    var resp = shipper.message
                    frappe.model.set_value('DTI Shipment Note', cur_frm.doc.name, 'shipper_contact_person_name', resp['shipper_contact_person_name']);
                    frappe.model.set_value('DTI Shipment Note', cur_frm.doc.name, 'shipper_company_name', resp['shipper_company_name']);
                    frappe.model.set_value('DTI Shipment Note', cur_frm.doc.name, 'shipper_contact_phone_number', resp['shipper_contact_phone_number']);
                    frappe.model.set_value('DTI Shipment Note', cur_frm.doc.name, 'shipper_address_street_lines', resp['shipper_address_street_lines']);
                    frappe.model.set_value('DTI Shipment Note', cur_frm.doc.name, 'shipper_address_city', resp['shipper_address_city']);
                    frappe.model.set_value('DTI Shipment Note', cur_frm.doc.name, 'shipper_address_state_or_province_code', resp['shipper_address_state_or_province_code']);
                    frappe.model.set_value('DTI Shipment Note', cur_frm.doc.name, 'shipper_address_country_code', resp['shipper_address_country_code']);
                    frappe.model.set_value('DTI Shipment Note', cur_frm.doc.name, 'shipper_address_postal_code', resp['shipper_address_postal_code']);
                });

            get_sales_order()
                .done(function (shipper) {
                    var resp = shipper.message
                    frappe.model.set_value('DTI Shipment Note', cur_frm.doc.name, 'sales_order', resp['against_sales_order']);
                });
        }
    }

)