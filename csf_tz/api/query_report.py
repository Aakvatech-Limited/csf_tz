import frappe

from frappe.desk.query_report import get_script as old_get_script

@frappe.whitelist()
def get_script(report_name):
    result = old_get_script(report_name)

    if not frappe.db.exists("AV Report Extension", report_name):
        return result

    av_report_extension_doc = frappe.get_doc("AV Report Extension", report_name)
    if av_report_extension_doc.active:
        if av_report_extension_doc.script:
            result["script"] = av_report_extension_doc.script
        if av_report_extension_doc.html_format:
            result["html_format"] = av_report_extension_doc.html_format

    return result
