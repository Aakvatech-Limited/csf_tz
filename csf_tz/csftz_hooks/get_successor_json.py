import json

import frappe
from frappe.query_builder.functions import Concat


def get_json(main_ancestor, ancestor_type="Accounts"):
    dt = frappe.qb.DocType("DocType")
    df = frappe.qb.DocType("DocField")
    cf = frappe.qb.DocType("Custom Field")

    docfield_query = (
        frappe.qb.from_(dt)
        .inner_join(df)
        .on(dt.name == df.parent)
        .select(
            Concat("erpnext.", dt.module, ".", dt.name).as_("name"),
            dt.name.as_("doctype_name"),
        )
        .where(df.options.isnotnull())
        .where(df.fieldtype == "Link")
        .where(dt.module == ancestor_type)
        .groupby(dt.module, dt.name)
    )

    custom_field_query = (
        frappe.qb.from_(dt)
        .inner_join(cf)
        .on(dt.name == cf.parent)
        .select(
            Concat("erpnext.", dt.module, ".", dt.name).as_("name"),
            dt.name.as_("doctype_name"),
        )
        .where(cf.options.isnotnull())
        .where(cf.fieldtype == "Link")
        .where(dt.module == ancestor_type)
        .groupby(dt.module, dt.name)
    )

    doc_list = docfield_query.union_all(custom_field_query).run(as_dict=True)

    for doc in doc_list:
        docfield_list = frappe.get_all(
            "DocField",
            filters={"parent": doc.doctype_name, "fieldtype": "Link"},
            fields="options",
            group_by="options",
        )
        custom_field_list = frappe.get_all(
            "Custom Field",
            filters={"parent": doc.doctype_name, "fieldtype": "Link"},
            fields="options",
            group_by="options",
        )
        doc["imports"] = []
        for options in docfield_list:
            options_string = (
                "erpnext."
                + frappe.get_value("DocType", doc.doctype_name, "module")
                + "."
                + options.get("options")
            )
            doc["imports"].append(options_string)
        for options in custom_field_list:
            options_string = (
                "erpnext."
                + frappe.get_value("DocType", doc.doctype_name, "module")
                + "."
                + options.get("options")
            )
            doc["imports"].append(options_string)

    return json.dumps(doc_list)
