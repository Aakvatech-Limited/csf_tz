// Get Value
function getValue (doctype, doc_name, field_name) {
    let res = null;
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            'doctype': doctype,
            'filters': { 'name': doc_name },
            'fieldname': field_name,
        },
        async: false,
        callback: function (r) {
            if (!r.exc) {
                res = r.message[field_name];
            }
            else {
                console.error(r.exc);
            }
        }
    });
    return res;
}

// Get Doc
function getDoc (doctype, doc_name) {
    let res = null;
    frappe.call({
        method: 'frappe.client.get',
        args: {
            'doctype': doctype,
            'name': doc_name,
        },
        async: false,
        callback: function (r) {
            if (!r.exc) {
                res = r.message;
            }
            else {
                console.error(r.exc);
            }
        }
    });
    return res;
}

// Get List
function getList (doctype, filters, fields, order_by, limit_page_length, limit_start) {
    let res = null;
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            'doctype': doctype,
            'filters': filters,
            'fields': fields,
            'order_by': order_by,
            'limit_page_length': limit_page_length,
            'limit_start': limit_start,
        },
        async: false,
        callback: function (r) {
            if (!r.exc) {
                res = r.message;
            }
            else {
                console.error(r.exc);
            }
        }
    });
    return res;
}
