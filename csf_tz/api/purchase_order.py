import frappe
from frappe import _


@frappe.whitelist()
def update_po_status(status, name):
    from erpnext.buying.doctype.purchase_order.purchase_order import update_status


    if status != "Submitted":
        update_status(status, name)
        return

    csf_tz_settings = frappe.get_doc("CSF TZ Settings")
    if csf_tz_settings.allow_reopen_of_po_based_on_role == 1:
        roles = frappe.get_roles()
        if csf_tz_settings.role_to_reopen_po and csf_tz_settings.role_to_reopen_po in roles:
            update_status(status, name)
        else:
            frappe.throw(_(f"You are not allowed to reopen this Purchase Order: <b>{name}</b>"))


@frappe.whitelist()
def close_or_unclose_purchase_orders(names, status):
    from erpnext.buying.doctype.purchase_order.purchase_order import close_or_unclose_purchase_orders

    if status != "Submitted":
        close_or_unclose_purchase_orders(names, status)
        return
    
    csf_tz_settings = frappe.get_doc("CSF TZ Settings")
    if csf_tz_settings.allow_reopen_of_po_based_on_role == 1:
        roles = frappe.get_roles()
        if csf_tz_settings.role_to_reopen_po and csf_tz_settings.role_to_reopen_po in roles:
            close_or_unclose_purchase_orders(names, status)
        else:
            frappe.throw(_("<b>You are not allowed to reopen Purchase Orders</b>"))


