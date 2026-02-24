import frappe
from frappe import _
from frappe.utils.csvutils import getlink
from frappe.model import core_doctypes_list

# List of excluded doctypes
excluded_doctype_list = ["Address", "Contact"]

def grant_dependant_access(doc, method):
    if frappe.flags.in_install or frappe.flags.in_migrate:
        return
    enable_dependent_auto_permission = frappe.db.get_single_value(
        "CSF TZ Settings", "enable_dependent_auto_permission"
    )
    if not enable_dependent_auto_permission:
        return
    if doc.dependent:
        frappe.msgprint(
            _(
                "Warning! {0} is a dependant doctype. If you wish to change access to it, remove it and add again."
            ).format(getlink("DocType", doc.parent))
        )
        return
    fields = frappe.get_meta(doc.parent).fields
    doctypes_granted_access = []
    for field in fields:
        if field.get("fieldtype") in ["Link"]:
            if create_custom_docperm(field.options, doc.role, doc.parent):
                doctypes_granted_access += [field.options]
        if field.get("fieldtype") in ["Table"]:
            child_fields = frappe.get_meta(field.options).fields
            for child_field in child_fields:
                if child_field.get("fieldtype") in ["Link"]:
                    if create_custom_docperm(child_field.options, doc.role, doc.parent):
                        doctypes_granted_access += [child_field.options]

    if len(doctypes_granted_access) > 0:
        frappe.msgprint(
            _(
                "Auto granted SELECT access to the following doctypes: "
                + str(doctypes_granted_access)
            )
        )

def create_custom_docperm(doctype, role, parent):
    # Return if doctype is in the excluded list
    if doctype in excluded_doctype_list:
        return
    
    if doctype == parent or doctype in core_doctypes_list:
        return
    is_permission_exists = frappe.get_all(
        "Custom DocPerm", filters={"parent": doctype, "role": role}
    )
    if len(is_permission_exists) > 0:
        return False
    custom_docperm = frappe.new_doc("Custom DocPerm")
    custom_docperm.parent = doctype
    custom_docperm.role = role
    custom_docperm.permlevel = 0
    custom_docperm.select = 1
    custom_docperm.read = 0
    custom_docperm.export = 0
    custom_docperm.dependent = 1
    custom_docperm.save()
    return True
