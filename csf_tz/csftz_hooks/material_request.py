import frappe
from frappe.query_builder import DocType
from frappe.utils import add_days, create_batch, nowdate
from frappe.utils.background_jobs import enqueue

cp = DocType("Company")
mr = DocType("Material Request")


def _auto_close_material_request_batch(material_request_names):
	for name in material_request_names:
		try:
			material_request_doc = frappe.get_doc("Material Request", name)
			material_request_doc.update_status("Stopped")
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"Auto Close Material Request Error: {name}")


def auto_close_material_request():
	"""
	Auto close Material Request based on settings specified on Company under section of stock settings
	"""

	def close_request_docs(date_before, row):
		material_requests = (
			frappe.qb.from_(mr)
			.select(mr.name)
			.where(
				(mr.docstatus == 1)
				& (mr.company == row.name)
				& (mr.status != "Stopped")
				& (mr.transaction_date <= date_before)
			)
		).run(as_dict=True)

		if len(material_requests) == 0:
			return

		for records in create_batch(material_requests, 100):
			enqueue(
				_auto_close_material_request_batch,
				queue="long",
				timeout=1200,
				job_name=f"auto_close_material_request_{row.name}_{records[0].name}",
				kwargs={"material_request_names": [record.name for record in records]},
			)

	company_details = (
		frappe.qb.from_(cp)
		.select(cp.name, cp.close_material_request_after)
		.where(cp.enable_auto_close_material_request == 1)
	).run(as_dict=True)

	if len(company_details) == 0:
		return

	for row in company_details:
		before_days = add_days(nowdate(), -row.close_material_request_after)
		close_request_docs(before_days, row)
