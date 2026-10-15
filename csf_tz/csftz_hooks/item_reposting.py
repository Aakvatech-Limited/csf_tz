import frappe
from erpnext.accounts.utils import update_gl_entries_after
from erpnext.stock.stock_ledger import update_entries_after
from frappe import _
from frappe.utils import getdate, today
from frappe.utils.background_jobs import enqueue


def get_reposting_start_date():
	"""Start date from CSF TZ Settings; throws when it is not set."""
	start_date = frappe.get_single("CSF TZ Settings").sle_gle_reposting_start_date
	if not start_date:
		frappe.throw(
			_("SLE GLE Reposting Start Date not set in {0}").format(
				frappe.utils.get_url_to_form("CSF TZ Settings", "CSF TZ Settings")
			)
		)
	return getdate(start_date)


def execute():
	posting_date = str(get_reposting_start_date())
	posting_time = "00:00:00"
	reposting_project_deployed_on = f"{posting_date} {posting_time}"

	if posting_date == today():
		return

	frappe.clear_cache()
	frappe.flags.warehouse_account_map = {}

	company_list = []

	sle = frappe.qb.DocType("Stock Ledger Entry")
	data = (
		frappe.qb.from_(sle)
		.select(
			sle.name,
			sle.item_code,
			sle.warehouse,
			sle.voucher_type,
			sle.voucher_no,
			sle.posting_date,
			sle.posting_time,
			sle.company,
		)
		.where(sle.creation > reposting_project_deployed_on)
		.where(sle.is_cancelled == 0)
		.orderby(sle.posting_date)
		.orderby(sle.posting_time)
		.orderby(sle.creation)
		.run(as_dict=True)
	)

	frappe.db.auto_commit_on_many_writes = 1
	print("Reposting Stock Ledger Entries...")
	total_sle = len(data)
	i = 0
	for d in data:
		if d.company not in company_list:
			company_list.append(d.company)

		update_entries_after(
			{
				"item_code": d.item_code,
				"warehouse": d.warehouse,
				"posting_date": d.posting_date,
				"posting_time": d.posting_time,
				"voucher_type": d.voucher_type,
				"voucher_no": d.voucher_no,
				"sle_id": d.name,
			},
			allow_negative_stock=True,
		)

		i += 1
		if i % 100 == 0:
			print(i, "/", total_sle)

	print("Reposting General Ledger Entries...")

	if data:
		for row in frappe.get_all("Company", filters={"enable_perpetual_inventory": 1}):
			if row.name in company_list:
				update_gl_entries_after(posting_date, posting_time, company=row.name)

	frappe.db.auto_commit_on_many_writes = 0


def get_creation_time():
	return frappe.db.sql(
		""" SELECT create_time FROM
		INFORMATION_SCHEMA.TABLES where TABLE_NAME = "tabRepost Item Valuation" """,
		as_list=1,
	)[0][0]


@frappe.whitelist()
def enqueue_reposting_sle_gle():
	get_reposting_start_date()
	frappe.msgprint(_("Reposting of SLE and GLE started"), alert=True)
	enqueue(method=execute, queue="long", timeout=10000, is_async=True)
