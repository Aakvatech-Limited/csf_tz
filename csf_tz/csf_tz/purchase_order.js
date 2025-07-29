frappe.require([
    '/assets/csf_tz/js/shortcuts.js',
    '/assets/csf_tz/js/po_shortcuts.js'
]);

frappe.ui.form.on("Purchase Order", {
    refresh: (frm) => {
        frappe.db.get_single_value("CSF TZ Settings", "limit_uom_as_item_uom").then(limit_uom_as_item_uom => {
            if (limit_uom_as_item_uom == 1) {
            frm.set_query("uom", "items", function (frm, cdt, cdn) {
                let row = locals[cdt][cdn];
                return {
                    query:
                        "erpnext.accounts.doctype.pricing_rule.pricing_rule.get_item_uoms",
                    filters: {
                        value: row.item_code,
                        apply_on: "Item Code",
                    },
                };
            });
            }
        });
    },
    supplier: function (frm) {
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
    setup: function (frm) {
        frm.set_query("taxes_and_charges", function () {
            return {
                "filters": {
                    "company": frm.doc.company,
                }
            };
        });
    },
});

frappe.ui.form.on("Purchase Order Item", {
    item_code: async function (frm, cdt, cdn) {
        var item = locals[cdt][cdn];
        var price_list = await get_price_list(frm, item.item_code, item.warehouse);
        frappe.model.set_value(cdt, cdn, "price_list_rate", price_list);
        frappe.model.set_value(cdt, cdn, "rate", price_list);
        frappe.model.set_value(cdt, cdn, "amount", price_list * item.qty);
    },
    warehouse: async function (frm, cdt, cdn) {
        var item = locals[cdt][cdn];
        var price_list = await get_price_list(frm, item.item_code, item.warehouse);
        frappe.model.set_value(cdt, cdn, "price_list_rate", price_list);
        frappe.model.set_value(cdt, cdn, "rate", price_list);
        frappe.model.set_value(cdt, cdn, "amount", price_list * item.qty);
    },
})

async function get_price_list(frm, item_code, warehouse) {
    var check = await frappe.db.get_single_value("CSF TZ Settings", "target_warehouse_based_price_list");
    if (check == 0) {
        return null;
    }
    if (!item_code || !warehouse || !frm.doc.supplier) {
        frappe.throw("Item Code, Warehouse and Supplier are required");
    }

    var price_list = await frappe.db.get_value("Dynamic Price List Assignment", { supplier: frm.doc.supplier, warehouse: warehouse }, "price_list");
    console.log(price_list);
    if (price_list.message.price_list) {
        var price_list_rate = await frappe.db.get_value("Item Price", { item_code: item_code, price_list: price_list.message.price_list }, "price_list_rate");
        if (price_list_rate.message.price_list_rate) {
            return price_list_rate.message.price_list_rate;
        } else {
            frappe.throw("Price List not found for Item " + item.item_code + ". Please create");
        }
    } else {
        frappe.throw("Price List not found. Please create one in Dynamic Price List Assignment for " + frm.doc.supplier + " and " + warehouse);
    }
}

frappe.ui.keys.add_shortcut({
    shortcut: 'ctrl+i',
    action: () => {
        ctrlI("Purchase Order Item");
    },
    page: this.page,
    description: __('Select Customer Item Price'),
    ignore_inputs: true,
});


frappe.ui.keys.add_shortcut({
    shortcut: 'ctrl+u',
    action: () => {
        ctrlU("Purchase Order Item");
    },
    page: this.page,
    description: __('Select Item Price'),
    ignore_inputs: true,
});

