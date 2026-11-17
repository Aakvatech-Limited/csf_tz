import frappe
import json
from frappe.query_builder.functions import Concat_ws

def get_json():

    doc_list = (
        get_link_doctypes_query("DocField").union_all(get_link_doctypes_query("Custom Field"))
    ).run(as_dict=True)
    
    for doc in doc_list:
        docfield_list = frappe.get_all("DocField", filters={"parent": doc.doctype_name, "fieldtype": "Link"}, fields="options", group_by="options")
        custom_field_list = frappe.get_all("Custom Field", filters={"parent": doc.doctype_name, "fieldtype": "Link"}, fields="options", group_by="options")
        doc["imports"] = []
        for options in docfield_list:
            options_string = "erpnext." + frappe.get_value("DocType", doc.doctype_name, "module") + "." + options.get("options")
            doc["imports"].append(options_string)
        for options in custom_field_list:
            options_string = "erpnext." + frappe.get_value("DocType", doc.doctype_name, "module") + "." + options.get("options")
            doc["imports"].append(options_string)

    return json.dumps(doc_list)


def get_link_doctypes_query(field_doctype):
    """DocTypes that have a Link field in `field_doctype`."""
    doctype = frappe.qb.DocType("DocType")
    field = frappe.qb.DocType(field_doctype)
    return (
        frappe.qb.from_(doctype)
        .inner_join(field)
        .on(doctype.name == field.parent)
        .select(
            Concat_ws(".", "erpnext", doctype.module, doctype.name).as_("name"),
            doctype.name.as_("doctype_name"),
        )
        .where(field.options.isnotnull())
        .where(field.fieldtype == "Link")
        .groupby(doctype.module, doctype.name)
    )
