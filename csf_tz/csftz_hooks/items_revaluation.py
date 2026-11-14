import frappe
from frappe.utils import flt


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
    """Incorrect entry of the item-warehouse whose first entry is earliest."""
    entries_by_item = {}
    for entry in get_stock_ledger_entries():
        entries_by_item.setdefault((entry.item_code, entry.warehouse), []).append(entry)

    incorrect = []
    for entries in entries_by_item.values():
        if row := get_incorrect_data(entries):
            first = entries[0]
            incorrect.append(
                ((first.posting_date, first.posting_time, first.creation), row)
            )

    return (
        min(incorrect, key=lambda started_row: started_row[0])[1] if incorrect else None
    )


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


@frappe.read_only()
def get_stock_ledger_entries():
    sle = frappe.qb.DocType("Stock Ledger Entry")
    index, order_by = get_posting_order_index()

    query = frappe.qb.from_(sle)
    if index:
        # the index isn't covering, so MariaDB would rather scan and sort the
        # whole ledger on disk
        query = query.force_index(index)

    query = query.select(
        sle.voucher_type,
        sle.voucher_no,
        sle.item_code,
        sle.actual_qty,
        sle.posting_date,
        sle.posting_time,
        sle.creation,
        sle.company,
        sle.warehouse,
        sle.qty_after_transaction,
        sle.batch_no,
    ).where(sle.is_cancelled == 0)

    for column in order_by:
        query = query.orderby(sle[column])

    return query.run(as_dict=True)


def get_posting_order_index():
    """An SLE index that returns each item-warehouse in posting order, and its order.

    ERPNext has had (posting_datetime, creation) and, from v15.64,
    (item_code, warehouse, posting_datetime, creation).
    """
    statistics = frappe.qb.Schema("information_schema").statistics
    index_columns = {}
    for row in (
        frappe.qb.from_(statistics)
        .select(statistics.index_name, statistics.column_name)
        .where(
            (statistics.table_schema == frappe.db.cur_db_name)
            & (statistics.table_name == "tabStock Ledger Entry")
        )
        .orderby(statistics.index_name)
        .orderby(statistics.seq_in_index)
        .run(as_dict=True)
    ):
        index_columns.setdefault(row.index_name, []).append(row.column_name)

    for prefix in (["item_code", "warehouse"], []):
        order_by = [*prefix, "posting_datetime", "creation"]
        for index, columns in index_columns.items():
            if columns[: len(order_by)] == order_by:
                return index, order_by

    return None, ["posting_date", "posting_time", "creation"]
