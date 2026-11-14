from itertools import groupby

import frappe
from erpnext.stock.report.incorrect_balance_qty_after_transaction.incorrect_balance_qty_after_transaction import (
    get_incorrect_data,
)

SLE_INDEX = "item_code_warehouse_posting_datetime_creation_index"


def process_incorrect_balance_qty():
    rec = get_first_incorrect_entry()
    if not rec:
        return

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


def get_first_incorrect_entry():
    """Incorrect entry of the item-warehouse whose first entry is earliest.

    Same pick as ordering the whole ledger by posting time, but each item-warehouse
    is read in index order, so the database never sorts the ledger on disk.
    """
    first = None
    for _key, entries in groupby(
        get_stock_ledger_entries(), key=lambda e: (e.item_code, e.warehouse)
    ):
        entries = list(entries)
        if not (row := get_incorrect_data(entries)):
            continue

        started = (entries[0].posting_datetime, entries[0].creation)
        if first is None or started < first[0]:
            first = (started, row)

    return first and first[1]


@frappe.read_only()
def get_stock_ledger_entries():
    sle = frappe.qb.DocType("Stock Ledger Entry")
    query = frappe.qb.from_(sle)

    # without the hint, MariaDB sorts the whole ledger on disk; index exists from ERPNext v15.64
    if frappe.db.has_index("tabStock Ledger Entry", SLE_INDEX):
        query = query.force_index(SLE_INDEX)

    return (
        query.select(
            sle.voucher_type,
            sle.voucher_no,
            sle.item_code,
            sle.actual_qty,
            sle.posting_date,
            sle.posting_time,
            sle.posting_datetime,
            sle.creation,
            sle.company,
            sle.warehouse,
            sle.qty_after_transaction,
            sle.batch_no,
        )
        .where(sle.is_cancelled == 0)
        .orderby(sle.item_code, sle.warehouse, sle.posting_datetime, sle.creation)
        .run(as_dict=True)
    )
