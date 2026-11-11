# Copyright (c) 2022, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from pypika import Table


class SQLProcess(Document):
    def validate(self):
        self.process = []

    @frappe.whitelist()
    def get_process(self):
        processlist = Table("processlist", schema="information_schema")
        return (
            frappe.qb.from_(processlist)
            .select(processlist.id, processlist.time, processlist.info)
            .where(processlist.info.isnotnull())
            .run(as_dict=True)
        )

    @frappe.whitelist()
    def kill_process(self, pid):
        frappe.msgprint(
            "Killing process {}".format(pid), alert=True, indicator="orange"
        )
        try:
            frappe.db.sql("""Kill {0}""".format(pid))
        except Exception:
            frappe.msgprint("Process not found", alert=True, indicator="red")
            return False
        frappe.msgprint("Process killed", alert=True, indicator="green")
        return True
