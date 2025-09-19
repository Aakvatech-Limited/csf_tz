# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now

class VehicleSyncTask(Document):
    @staticmethod
    def clear_old_logs(days=7):
        table = frappe.qb.DocType("Vehicle Sync Task")
        frappe.db.delete(table, filters=(table.creation < (Now() - Interval(days=days))))