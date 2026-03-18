import click
import frappe
from frappe import _
from csf_tz.vfd_providers.doctype.vfdplus_settings.vfdplus_settings import (
    get_payload as get_vfdplus_payload,
    post_fiscal_receipt as vfdplus_post_fiscal_receipt
)
from csf_tz.vfd_providers.doctype.total_vfd_setting.total_vfd_setting import (
    get_payload as get_total_vfd_payload,
    post_fiscal_receipt as total_vfd_post_fiscal_receipt
)
from csf_tz.vfd_providers.doctype.simplify_vfd_settings.simplify_vfd_settings import (
    get_payload as get_simplify_payload,
    post_fiscal_receipt as simplify_vfd_post_fiscal_receipt
)


@frappe.whitelist()
def generate_tra_vfd(docname, sinv_doc=None, method="POST", caller="Frontend"):
    if not sinv_doc:
        sinv_doc = frappe.get_doc("Sales Invoice", docname)
    
    if sinv_doc.is_not_vfd_invoice or sinv_doc.vfd_status == "Success" or sinv_doc.is_return == 1:
        return
    
    comp_vfd_provider = frappe.get_cached_doc("Company VFD Provider", sinv_doc.company)
    if not comp_vfd_provider:
        return
    
    vfd_provider = frappe.get_cached_doc("VFD Provider", comp_vfd_provider.vfd_provider)
    if not vfd_provider:
        return
    
    vfd_provider_settings = vfd_provider.vfd_provider_settings
    if not vfd_provider_settings:
        return

    settings_info = frappe.get_cached_value(
        vfd_provider_settings,
        sinv_doc.company,
        ["enable_vfd_preview", "vfd_start_date"],
        as_dict=True
    )

    if not settings_info.get("vfd_start_date"):
        frappe.throw(_(f"Please set VFD Start Date in <b>{vfd_provider_settings}</b>"))
    
    if frappe.utils.getdate(sinv_doc.posting_date) < settings_info.get("vfd_start_date"):
        frappe.throw(
            _(
                f"VFD cannot be generated for Invoice before <b>{settings_info.get('vfd_start_date')}</b> \
                as per the settings in <b>{vfd_provider_settings}</b>"
            )
        )
    
    if settings_info.get("enable_vfd_preview") == 1 and caller == "Frontend":
        payload = {}
        if vfd_provider.name == "VFDPlus":
            payload = get_vfdplus_payload(sinv_doc)
        
        elif vfd_provider.name == "TotalVFD":
            payload = get_total_vfd_payload(sinv_doc)
        
        elif vfd_provider.name == "SimplifyVFD":
            payload = get_simplify_payload(sinv_doc)
        else:
            frappe.throw(_("VFD Provider not supported"))
        
        return {"data": payload, "vfd_provider": vfd_provider.name, "preview": True}
    
    else:
        if vfd_provider.name == "VFDPlus":
            return vfdplus_post_fiscal_receipt(doc=sinv_doc, method=method)
        
        elif vfd_provider.name == "TotalVFD":
            return total_vfd_post_fiscal_receipt(doc=sinv_doc, method=method)

        elif vfd_provider.name == "SimplifyVFD":
            return simplify_vfd_post_fiscal_receipt(doc=sinv_doc, method=method)
        else:
            frappe.throw(_("VFD Provider not supported"))


def autogenerate_vfd(doc, method):
    if doc.is_not_vfd_invoice or doc.vfd_status == "Success" or doc.is_return == 1:
        return
    
    if doc.is_auto_generate_vfd and doc.docstatus == 1:
        generate_tra_vfd(docname=doc.name, sinv_doc=doc, method=method, caller="Scheduler")


def posting_all_vfd_invoices():
    if frappe.local.flags.vfd_posting:
        frappe.log_error(_("VFD Posting Flag found", "VFD Posting Flag found"))
        return
    
    frappe.local.flags.vfd_posting = True

    companies = frappe.get_all("Company", pluck="name")
    for company in companies:
        comp_vfd_provider = None
        if frappe.db.exists("Company VFD Provider", company):
            comp_vfd_provider = frappe.get_cached_doc("Company VFD Provider", company)
        else:
            continue

        vfd_provider = frappe.get_cached_doc("VFD Provider", comp_vfd_provider.vfd_provider)

        vfd_provider_settings = vfd_provider.vfd_provider_settings
        if not vfd_provider_settings:
            continue

        vfd_start_date = frappe.get_cached_value(
            vfd_provider_settings,
            company,
            "vfd_start_date"
        )

        if not vfd_start_date:
            continue

        invoices = frappe.db.get_all(
            "Sales Invoice",
            filters={
                "docstatus": 1,
                "company": company,
                "is_not_vfd_invoice": 0,
                "is_return": 0,
                "vfd_status": ["not in", ["Not Sent", "Success"]],
                "posting_date": [">=", vfd_start_date]
            }
        )

        for invoice in invoices:
            doc = frappe.get_doc("Sales Invoice", invoice.name)

            if vfd_provider.name == "VFDPlus":
                vfdplus_post_fiscal_receipt(doc=doc, method="POST")
            
            elif vfd_provider.name == "TotalVFD":
                total_vfd_post_fiscal_receipt(doc=doc, method="POST")
            
            elif vfd_provider.name == "SimplifyVFD":
                simplify_vfd_post_fiscal_receipt(doc=doc, method="POST")

            else:
                continue
    
    frappe.local.flags.vfd_posting = False


def clean_and_update_tax_id_info(doc, method):
    cleaned_tax_id = "".join(char for char in (doc.tax_id or "") if char.isdigit())
    doc.tax_id = cleaned_tax_id
    if doc.tax_id:
        doc.vfd_cust_id_type = "1- TIN"
        doc.vfd_cust_id = doc.tax_id
    else:
        doc.vfd_cust_id_type = "6- Other"
        doc.vfd_cust_id = "999999999"
