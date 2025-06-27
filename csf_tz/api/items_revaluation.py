import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def get_data(filters):
    filters = frappe._dict(filters)
    data = get_stock_ledger_entries(filters)
    itewise_balance_qty = {}

    for row in data:
        key = (row.item_code, row.warehouse)
        itewise_balance_qty.setdefault(key, []).append(row)

    res = validate_data(itewise_balance_qty)
    return res


def validate_data(itewise_balance_qty):
    res = []
    for key, data in itewise_balance_qty.items():
        row = get_incorrect_data(data)
        if row:
            res.append(row)

    return res


def get_incorrect_data(data):
    balance_qty = 0.0
    for row in data:
        balance_qty += row.actual_qty
        if row.voucher_type == "Stock Reconciliation" and not row.batch_no:
            balance_qty = flt(row.qty_after_transaction)

        row.expected_balance_qty = balance_qty
        if abs(flt(row.expected_balance_qty) - flt(row.qty_after_transaction)) > 0.5:
            row.differnce = abs(
                flt(row.expected_balance_qty) - flt(row.qty_after_transaction)
            )
            return row


def get_stock_ledger_entries(report_filters):
    filters = {"is_cancelled": 0}
    fields = [
        "name",
        "voucher_type",
        "voucher_no",
        "item_code",
        "actual_qty",
        "posting_date",
        "posting_time",
        "company",
        "warehouse",
        "qty_after_transaction",
        "batch_no",
    ]

    for field in ["warehouse", "item_code", "company"]:
        if report_filters.get(field):
            filters[field] = report_filters.get(field)

    return frappe.get_all(
        "Stock Ledger Entry",
        fields=fields,
        filters=filters,
        order_by="timestamp(posting_date, posting_time) asc, creation asc",
    )


def process_incorrect_balance_qty():
    data = get_data({})
    if len(data) > 0:
        rec = frappe._dict(data[0])
        doc = frappe.new_doc("Repost Item Valuation")
        doc.based_on = "Transaction"
        doc.voucher_type = rec.voucher_type
        doc.voucher_no = rec.voucher_no
        doc.posting_date = rec.posting_date
        doc.posting_time = rec.posting_time
        doc.company = rec.company
        doc.warehouse = rec.warehouse
        doc.allow_negative_stock = 1
        doc.docstatus = 1
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
