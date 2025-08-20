frappe.require([
    '/assets/csf_tz/js/csfUtlis.js',
    '/assets/csf_tz/js/shortcuts.js'
]);

frappe.ui.form.on("Sales Order", {
    onload: async function(frm) {
    try {
        // cache the promise so other events can await it
        frm.__csf_settings_promise = frappe.db.get_doc("CSF TZ Settings", "CSF TZ Settings");
        const settings = await frm.__csf_settings_promise;
        frm.csf_settings = settings;
    } catch (e) {
        console.warn("Failed to preload CSF TZ Settings", e);
        frm.csf_settings = null;
    }
    },
    refresh: async function (frm) {
        if (!frm.csf_settings) {
            try {
                frm.csf_settings = await (frm.__csf_settings_promise ||
                    frappe.db.get_doc("CSF TZ Settings", "CSF TZ Settings"));
            } catch (e) {
                console.warn("No CSF settings available at refresh time");
            }
        }

        if (frm.csf_settings && frm.csf_settings.limit_uom_as_item_uom == 1) {
            frm.set_query("uom", "items", function (frm, cdt, cdn) {
                let row = locals[cdt][cdn];
                return {
                    query: "erpnext.accounts.doctype.pricing_rule.pricing_rule.get_item_uoms",
                    filters: {
                        value: row.item_code,
                        apply_on: "Item Code",
                    },
                };
            });
        }
    },

    customer: async function (frm) {
        if (!frm.doc.customer) return;

        // ensure settings are available here too
        const settings = frm.csf_settings || (frm.__csf_settings_promise && await frm.__csf_settings_promise);

        if (settings && settings.show_customer_outstanding_in_sales_order == 1) {
            frappe.call({
                method: 'csf_tz.csftz_hooks.customer.get_customer_total_unpaid_amount',
                args: {
                    customer: frm.doc.customer,
                    company: frm.doc.company,
                },
                callback: function (r) {
                    if (r.message) console.info(r.message);
                }
            });
        } else {
            console.info("Skipping outstanding check: settings unavailable or disabled.");
        }
        setTimeout(function () {
            if (!frm.doc.tax_category) {
                frappe.call({
                    method: "csf_tz.custom_api.get_tax_category",
                    args: {
                        doc_type: frm.doc.doctype,
                        company: frm.doc.company,
                    },
                    callback: function (r) {
                        if (!r.exc) {
                            frm.set_value("tax_category", r.message);
                            frm.trigger("tax_category");
                        }
                    }
                });
            }
        }, 1000);
    },
    default_item_discount: function (frm) {
        frm.doc.items.forEach(item => {
            frappe.model.set_value(item.doctype, item.name, 'discount_percentage', frm.doc.default_item_discount);
        });
    },
});

frappe.ui.keys.add_shortcut({
    shortcut: 'ctrl+q',
    action: () => {
        ctrlQ("Sales Order Item");
    },
    page: this.page,
    description: __('Select Item Warehouse'),
    ignore_inputs: true,
});

frappe.ui.keys.add_shortcut({
    shortcut: 'ctrl+i',
    action: () => {
        ctrlI("Sales Order Item");
    },
    page: this.page,
    description: __('Select Customer Item Price'),
    ignore_inputs: true,
});


frappe.ui.keys.add_shortcut({
    shortcut: 'ctrl+u',
    action: () => {
        ctrlU("Sales Order Item");
    },
    page: this.page,
    description: __('Select Item Price'),
    ignore_inputs: true,
});