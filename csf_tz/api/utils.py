from __future__ import unicode_literals

import frappe


def msgThrow(msg, method="throw", alert=True):
	if method == "validate":
		frappe.msgprint(msg, alert=alert)
	else:
		frappe.throw(msg)


def msgPrint(msg, method="throw", alert=False):
	if method == "validate":
		frappe.msgprint(msg, alert=True)
	else:
		frappe.msgprint(msg, alert=alert)
