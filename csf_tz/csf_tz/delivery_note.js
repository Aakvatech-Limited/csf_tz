frappe.ui.keys.add_shortcut({
    shortcut: 'ctrl+q',
    action: () => {
            const current_doc = $('.data-row.editable-row').parent().attr("data-name");
            const item_row = locals["Delivery Note Item"][current_doc];
            frappe.call({
                method: 'csf_tz.custom_api.get_item_info',
                args: {item_code: item_row.item_code},
                callback: function(r) {
                    if (r.message.length > 0){
                        const d = new frappe.ui.Dialog({
                            title: __('Item Balance'),
                            width: 600
                        });
                        $(`<div class="modal-body ui-front">
                            <h2>${item_row.item_code} : ${item_row.qty}</h2>
                            <p>Choose Warehouse and click Select :</p>
                            <table class="table table-bordered">
                            <thead>
                            </thead>
                            <tbody>
                            </tbody>
                            </table>
                        </div>`).appendTo(d.body);
                        const thead = $(d.body).find('thead');
                        if (r.message[0].batch_no){
                            r.message.sort((a,b) => a.expiry_status-b.expiry_status);
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
                                <td>${item_row.stock_uom }</td>
                            </tr>
                            `).appendTo(tbody);
                            if (element.batch_no) {
                                $(`
                                    <td>${element.batch_no}</td>
                                    <td>${element.expires_on}</td>
                                    <td>${element.expiry_status }</td>
                                `).appendTo(tr);
                                tr.find('.check-warehouse').attr('data-batch',element.batch_no);
                                tr.find('.check-warehouse').attr('data-batchQty',element.actual_qty);
                            }
                            tbody.find('.check-warehouse').on('change', function() {
                                $('input.check-warehouse').not(this).prop('checked', false);
                            });
                        });
                        d.set_primary_action("Select", function() {
                            $(d.body).find('input:checked').each(function(i, input) {
                                frappe.model.set_value(item_row.doctype, item_row.name, 'warehouse', $(input).attr('data-warehouse'));
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
                        frappe.show_alert({message:__('There is No Records'), indicator:'red'}, 5);
                    }
                }
            });
    },
    page: this.page,
    description: __('Select Item Warehouse'),
    ignore_inputs: true,
});



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
