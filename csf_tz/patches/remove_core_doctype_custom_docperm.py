from __future__ import unicode_literals
import frappe


def execute():
    custom_docperm = frappe.qb.DocType("Custom DocPerm")
    frappe.qb.from_(custom_docperm).delete().where(custom_docperm.name != "a").where(
        custom_docperm.parent.isin(["DocType", "Patch Log", "Module Def", "Transaction Log"])
    ).run()
