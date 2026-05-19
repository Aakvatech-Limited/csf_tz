frappe.ui.form.on("Delivery Note", {
	refresh: function(frm, dt, dn) {
		if ((!frm.is_return) && (frm.status!="Closed" || frm.is_new())) {
			if (frm.doc.docstatus===0) {
                let query_args = {
                    query:"csf_tz.custom_api.get_pending_sales_invoice",
                    filters: {
                        company: frm.doc.company,
                        set_warehouse: frm.doc.set_warehouse || ""
                    }
                }
				frm.add_custom_button(__('Sales Invoice'),
					function() {
						erpnext.utils.map_current_doc({
                            method: "csf_tz.custom_api.make_delivery_note",
							source_doctype: "Sales Invoice",
							target: frm,
							setters: {
                                customer: frm.doc.customer || undefined,
                                set_warehouse: frm.doc.set_warehouse || "",
                            },
                            date_field: "posting_date",
                            get_query() {
                                return query_args;
                            },
						})
					}, __("Get items from"));
			}
		}

    },
    customer: function(frm) {
        if (!frm.doc.customer) {
            return
        }
        setTimeout(function() {
            if (!frm.doc.tax_category){
                frappe.call({
                    method: "csf_tz.custom_api.get_tax_category",
                    args: {
                        doc_type: frm.doc.doctype,
                        company: frm.doc.company,
                    },
                    callback: function(r) {
                        console.log(r.message);
                        if(!r.exc) {
                            frm.set_value("tax_category", r.message);
                            frm.trigger("tax_category");
                        }
                    }
                });
        }
          }, 1000);
    },
});
