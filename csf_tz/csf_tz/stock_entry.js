frappe.require([
    '/assets/csf_tz/js/shortcuts.js'
]);

frappe.ui.form.on("Stock Entry", {
    setup: function (frm) {
        frm.trigger("set_warehouse_options");
    },
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
    onload: function (frm) {
        if (frm.docstatus == 0) {
            frm.trigger("stock_entry_type");
            frm.set_query("repack_template", function () {
                return {
                    "filters": {
                        "docstatus": 1
                    }
                };
            });
            frm.trigger("set_warehouse_options");
        }
    },
    company: function (frm) {
        frm.trigger("set_warehouse_options");
    },
    repack_template: function (frm) {
        frm.trigger("get_repack_template");
    },
    repack_qty: function (frm) {
        frm.trigger("get_repack_template");
    },
    get_repack_template: function (frm) {
        if (!frm.doc.repack_template || !frm.doc.repack_qty) { return }
        frappe.call({
            method: 'csf_tz.custom_api.get_repack_template',
            args: {
                template_name: frm.doc.repack_template,
                qty: frm.doc.repack_qty,
            },
            callback: function (r) {
                frm.clear_table("items");
                r.message.forEach(d => {
                    const child = frm.add_child("items");
                    frappe.model.set_value(child.doctype, child.name, "item_code", d.item_code)
                    frappe.model.set_value(child.doctype, child.name, "qty", d.qty)
                    frappe.model.set_value(child.doctype, child.name, "uom", d.item_uom)
                    if (d.s_warehouse) {
                        frappe.model.set_value(child.doctype, child.name, "s_warehouse", d.s_warehouse)
                    }
                    if (d.t_warehouse) {
                        frappe.model.set_value(child.doctype, child.name, "t_warehouse", d.t_warehouse)
                    }
                });

            }
        });
        frm.refresh_field("items");
    },
    stock_entry_type: function (frm) {
        if (frm.doc.stock_entry_type == "Repack from template") {
            frappe.meta.get_docfield("Stock Entry Detail", "item_code", frm.doc.name).read_only = 1;
            frappe.meta.get_docfield("Stock Entry Detail", "item_group", frm.doc.name).read_only = 1;
            $('.grid-add-multiple-rows').hide();
            $('.grid-add-row').hide();
            $('.grid-remove-rows').hide();
            $('.grid-download').hide();
            $('.grid-upload').hide();
            frm.toggle_reqd("qty", frm.doc.stock_entry_type == "Repack from template" ? 1 : 0);
        } else {
            frappe.meta.get_docfield("Stock Entry Detail", "item_code", frm.doc.name).read_only = 0;
            frappe.meta.get_docfield("Stock Entry Detail", "item_group", frm.doc.name).read_only = 0;
            $('.grid-add-multiple-rows').show();
            $('.grid-add-row').show();
            $('.grid-remove-rows').show();
            $('.grid-download').show();
            $('.grid-upload').show();
            frm.toggle_reqd("qty", frm.doc.stock_entry_type == "Repack from template" ? 1 : 0);
        }
        if (["Repack from template", "Manufacture"].includes(frm.doc.stock_entry_type)) {
            frm.set_df_property('total_net_weight', 'hidden', 1)
        }
        else {
            frm.set_df_property('total_net_weight', 'hidden', 0)
        }
        frm.refresh_field("items");
        frm.refresh();
    },
    calculate_net_weight: function (frm) {
        frm.doc.total_net_weight = 0.0;

        $.each(frm.doc["items"] || [], function (i, item) {
            frm.doc.total_net_weight += flt(item.total_weight);
        });
        refresh_field("total_net_weight");
    },
    set_warehouse_options: function (frm) {
        frappe.call({
            "method": "csf_tz.custom_api.get_warehouse_options",
            "args": { company: frm.doc.company },
            callback: function (r) {
                if (r.message && r.message.length) {
                    // frappe.meta.get_docfield("ModulesT", "module", frm.doc.name).options = r.message;
                    // frm.get_docfield("taxes", "rate").reqd = 0;
                    frm.set_df_property("final_destination", "options", r.message);
                }
            }
        });
    },
});

frappe.ui.form.on("Stock Entry Detail", {
    conversion_factor: function (frm, cdt, cdn) {
        var item = frappe.get_doc(cdt, cdn);
        item.total_weight = flt(item.transfer_qty * item.weight_per_unit * item.conversion_factor);
        refresh_field("total_weight");
        frm.trigger("calculate_net_weight");
    },
    qty: function (frm, cdt, cdn) {
        frm.script_manager.trigger("conversion_factor", cdt, cdn);
    },
});
frappe.ui.keys.add_shortcut({
    shortcut: 'ctrl+q',
    action: () => {
        const current_doc = $('.data-row.editable-row').parent().attr("data-name");
        const item_row = locals["Stock Entry Detail"][current_doc];
        frappe.call({
            method: 'csf_tz.custom_api.get_item_info',
            args: { item_code: item_row.item_code },
            callback: function (r) {
                if (r.message.length > 0) {
                    const d = new frappe.ui.Dialog({
                        title: __('Item Balance'),
                        width: 600
                    });
                    $(`<div class="modal-body ui-front">
                            <h2>${item_row.item_code} : ${item_row.item_name}</h2>
                            <p>Choose Warehouse and click Select :</p>
                            <table class="table table-bordered">
                            <thead>
                            </thead>
                            <tbody>
                            </tbody>
                            </table>
                        </div>`).appendTo(d.body);
                    const thead = $(d.body).find('thead');
                    if (r.message[0].batch_no) {
                        r.message.sort((a, b) => a.expiry_status - b.expiry_status);
                        $(`<tr>
                            <th>Check</th>
                            <th>Warehouse</th>
                            <th>Qty</th>
                            <th>UOM</th>
                            <th>Batch No</th>
                            <th>Expires On</th>
                            <th>Expires in Days</th>
                            </tr>`).appendTo(thead);
                    } else {
                        $(`<tr>
                            <th>Check</th>
                            <th>Warehouse</th>
                            <th>Qty</th>
                            <th>UOM</th>
                            </tr>`).appendTo(thead);
                    }
                    r.message.forEach(element => {
                        const tbody = $(d.body).find('tbody');
                        const tr = $(`
                            <tr>
                                <td><input type="checkbox" class="check-warehouse" data-warehouse="${element.warehouse}"></td>
                                <td>${element.warehouse}</td>
                                <td>${element.actual_qty}</td>
                                <td>${item_row.stock_uom}</td>
                            </tr>
                            `).appendTo(tbody);
                        if (element.batch_no) {
                            $(`
                                    <td>${element.batch_no}</td>
                                    <td>${element.expires_on}</td>
                                    <td>${element.expiry_status}</td>
                                `).appendTo(tr);
                            tr.find('.check-warehouse').attr('data-batch', element.batch_no);
                            tr.find('.check-warehouse').attr('data-batchQty', element.actual_qty);
                        }
                        tbody.find('.check-warehouse').on('change', function () {
                            $('input.check-warehouse').not(this).prop('checked', false);
                        });
                    });
                    d.set_primary_action("Select", function () {
                        $(d.body).find('input:checked').each(function (i, input) {
                            frappe.model.set_value(item_row.doctype, item_row.name, 's_warehouse', $(input).attr('data-warehouse'));
                            if ($(input).attr('data-batch')) {
                                frappe.model.set_value(item_row.doctype, item_row.name, 'batch_no', $(input).attr('data-batch'));
                            }
                        });
                        cur_frm.rec_dialog.hide();
                        cur_frm.refresh_fields();
                    });
                    cur_frm.rec_dialog = d;
                    d.show();
                }
                else {
                    frappe.show_alert({ message: __('There is No Records'), indicator: 'red' }, 5);
                }
            }
        });
    },
    page: this.page,
    description: __('Select Item Warehouse'),
    ignore_inputs: true,
});