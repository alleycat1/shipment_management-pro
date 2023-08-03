frappe.ui.form.on("Sales Order", {
    refresh: function (frm) {
        if (frm.doc.tracking_ids) {
            frm.add_custom_button(__('Track Shipments'),
                function () {
                    var url = "https://www.fedex.com/apps/fedextrack/?action=track&tracknumbers=" + frm.doc.tracking_ids + "&locale=en_US&cntry_code=us"
                    window.open(url, "_blank");
                }).addClass("btn btn-primary");
        }
    }
})