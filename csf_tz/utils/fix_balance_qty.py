import frappe
from erpnext.stock.stock_ledger import get_previous_sle_of_current_voucher
from frappe.query_builder.functions import CombineDatetime
from frappe.utils import add_to_date, now


def has_correct_balance_qty(previous_sle, sles):
	balance_qty = previous_sle.qty_after_transaction
	for sle in sles:
		if sle.item_code == previous_sle.item_code and sle.warehouse == previous_sle.warehouse:
			if sle.voucher_type == "Stock Reconciliation" and not (sle.serial_no or sle.batch_no):
				balance_qty = sle.qty_after_transaction
			else:
				balance_qty += sle.actual_qty

			if balance_qty != sle.qty_after_transaction:
				return False

	return True


# nosemgrep: frappe-semgrep-rules.rules.overusing-args
def create_repost_item_valuation_entry(args):
	args = frappe._dict(args)
	repost_entry = frappe.new_doc("Repost Item Valuation")
	repost_entry.based_on = "Item and Warehouse"
	repost_entry.item_code = args.item_code
	repost_entry.warehouse = args.warehouse
	repost_entry.posting_date = args.posting_date
	repost_entry.posting_time = args.posting_time
	repost_entry.company = args.company
	repost_entry.allow_negative_stock = 1
	repost_entry.flags.ignore_links = True
	repost_entry.flags.ignore_permissions = True
	repost_entry.save()
	repost_entry.submit()


from_time = add_to_date(now(), hours=-2)

# nosemgrep: frappe-semgrep-rules.rules.frappe-breaks-multitenancy
table = frappe.qb.DocType("Stock Ledger Entry")
# nosemgrep: frappe-semgrep-rules.rules.frappe-breaks-multitenancy
sles = (
	frappe.qb.from_(table)
	.select(
		table.item_code,
		table.warehouse,
		table.voucher_type,
		table.voucher_no,
		table.posting_date,
		table.posting_time,
		table.qty_after_transaction,
	)
	.where((table.is_cancelled == 0) & (CombineDatetime(table.posting_date, table.posting_time) >= from_time))
	.orderby(CombineDatetime(table.posting_date, table.posting_time))
	.orderby(table.creation)
).run(as_dict=True)

checked_item_warehouse = []

for sle in sles:
	if [sle.item_code, sle.warehouse] in checked_item_warehouse:
		continue

	checked_item_warehouse.append([sle.item_code, sle.warehouse])

	previous_sle = get_previous_sle_of_current_voucher(sle, exclude_current_voucher=True)

	if not has_correct_balance_qty(previous_sle, sles):
		create_repost_item_valuation_entry(previous_sle)
