import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.utils.background_jobs import enqueue
from frappe.utils import add_days, nowdate, create_batch
from erpnext.stock.doctype.material_request.material_request import update_status


cp = DocType("Company")
mr = DocType("Material Request")

@frappe.whitelist()
def update_mr_status(name, status):
    if status != "Submitted":
        update_status(name, status)
        return

    csf_tz_settings = frappe.get_doc("CSF TZ Settings")
    if csf_tz_settings.allow_reopen_of_material_request_based_on_role == 1:
        roles = frappe.get_roles()
        if csf_tz_settings.role_to_reopen_material_request and csf_tz_settings.role_to_reopen_material_request in roles:
            update_status(name, status)
        else:
            frappe.throw(_(f"You are not allowed to reopen this Material Request: <b>{name}</b>"))



def auto_close_material_request():
    """
    Auto close Material Request based on settings specified on Company under section of stock settings
    """

    def close_request_docs(date_before, row):
        material_requests = (
            frappe.qb.from_(mr)
            .select(
                mr.name
            )
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
            for record in records:
                try:
                    material_request_doc = frappe.get_doc("Material Request", record.name)
                    material_request_doc.update_status("Stopped")
                
                except Exception as e:
                    frappe.log_error(frappe.get_traceback(), f"Auto Close Material Request Error: {record.name}")

    company_details = (
        frappe.qb.from_(cp)
        .select(
            cp.name,
            cp.close_material_request_after
        )
        .where(
            cp.enable_auto_close_material_request == 1
        )
    ).run(as_dict=True)
    
    if len(company_details) == 0:
        return
    
    for row in company_details:
        before_days = add_days(nowdate(), -row.close_material_request_after)
        close_request_docs(before_days, row)
