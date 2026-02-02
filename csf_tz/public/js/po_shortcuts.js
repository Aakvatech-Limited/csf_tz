function ctrlI(TableName) {
    // Get the current document details
    const current_doc = $('.data-row.editable-row').parent().attr("data-name");
    const item_row = locals[TableName][current_doc];

    // Prepare filters for the query
    const filters = {
        item_code: item_row.item_code,
        customer: cur_frm.doc.customer || "",
        currency: cur_frm.doc.currency,
        company: cur_frm.doc.company
    };

    // Call the custom API to fetch data
    frappe.call({
        method: "csf_tz.custom_api.get_item_prices_custom_po",
        args: { filters: filters },
        callback: function (response) {
            if (response.message && response.message.length > 0) {
                const e = new frappe.ui.Dialog({
                    title: __('Item Prices'),
                    width: 600
                });

                $(`<div class="modal-body ui-front">
                            <h2>${item_row.item_code} : ${item_row.item_name}</h2>
                            <p>Choose Price and click Select :</p>
                            <table class="table table-bordered">
                            <thead>
                            </thead>
                            <tbody>
                            </tbody>
                            </table>
                        </div>`).appendTo(e.body);

                const thead = $(e.body).find('thead');
                $(`<tr>
                            <th>Check</th>
                            <th>Rate</th>
                            <th>Qty</th>
                            <th>Date</th>
                            <th>Invoice</th>
                            <th>Customer</th>
                        </tr>`).appendTo(thead);

                response.message.forEach(element => {
                    const tbody = $(e.body).find('tbody');
                    const tr = $(`
                            <tr>
                                <td><input type="checkbox" class="check-rate" data-rate="${element.rate}"></td>
                                <td>${element.rate}</td>
                                <td>${element.qty}</td>
                                <td>${element.posting_date}</td>
                                <td>${element.invoice}</td>
                                <td>${element.customer}</td>
                            </tr>
                            `).appendTo(tbody);

                    tbody.find('.check-rate').on('change', function () {
                        $('input.check-rate').not(this).prop('checked', false);
                    });
                });

                e.set_primary_action("Select", function () {
                    $(e.body).find('input:checked').each(function (i, input) {
                        frappe.model.set_value(item_row.doctype, item_row.name, 'rate', $(input).attr('data-rate'));
                    });
                    cur_frm.rec_dialog.hide();
                    cur_frm.refresh_fields();
                });

                cur_frm.rec_dialog = e;
                e.show();
            } else {
                frappe.msgprint({
                    message: "No rates found for the given filters.",
                    title: "Warning",
                    indicator: "orange"
                });
            }
        },
        error: function (error) {
            // Handle errors
            frappe.msgprint({
                message: "Error fetching rates. Please try again.",
                title: "Error",
                indicator: "red"
            });
            console.error(error);
        }
    });
}

function ctrlU (TableName) {
    const current_doc = $('.data-row.editable-row').parent().attr("data-name");
    const item_row = locals[TableName][current_doc];
    frappe.call({
        method: 'csf_tz.custom_api.get_item_prices_po',
        args: {
            item_code: item_row.item_code,
            currency: cur_frm.doc.currency,
            company: cur_frm.doc.company
        },
        callback: function (r) {
            if (r.message.length > 0) {
                const e = new frappe.ui.Dialog({
                    title: __('Item Prices'),
                    width: 600
                });
                $(`<div class="modal-body ui-front">
                            <h2>${item_row.item_code} : ${item_row.qty}</h2>
                            <p>Choose Price and click Select :</p>
                            <table class="table table-bordered">
                            <thead>
                            </thead>
                            <tbody>
                            </tbody>
                            </table>
                        </div>`).appendTo(e.body);
                const thead = $(e.body).find('thead');
                $(`<tr>
                            <th>Check</th>
                            <th>Rate</th>
                            <th>Qty</th>
                            <th>Date</th>
                            <th>Invoice</th>
                            <th>Customer</th>
                        </tr>`).appendTo(thead);
                r.message.forEach(element => {
                    const tbody = $(e.body).find('tbody');
                    const tr = $(`
                            <tr>
                                <td><input type="checkbox" class="check-rate" data-rate="${element.price}"></td>
                                <td>${element.price}</td>
                                <td>${element.qty}</td>
                                <td>${element.date}</td>
                                <td>${element.invoice}</td>
                                <td>${element.customer}</td>
                            </tr>
                            `).appendTo(tbody);

                    tbody.find('.check-rate').on('change', function () {
                        $('input.check-rate').not(this).prop('checked', false);
                    });
                });
                e.set_primary_action("Select", function () {
                    $(e.body).find('input:checked').each(function (i, input) {
                        frappe.model.set_value(item_row.doctype, item_row.name, 'rate', $(input).attr('data-rate'));
                    });
                    cur_frm.rec_dialog.hide();
                    cur_frm.refresh_fields();
                });
                cur_frm.rec_dialog = e;
                e.show();
            }
            else {
                frappe.show_alert({ message: __('There are no records'), indicator: 'red' }, 5);
            }
        }
    });
}