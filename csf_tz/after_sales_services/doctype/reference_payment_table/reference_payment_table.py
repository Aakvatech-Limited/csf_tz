# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ReferencePaymentTable(Document):
	pass
	

def update_child_table(self, fieldname, df=None):
	'''Updated function to prevent saving of approved or rejected funds request'''
	'''sync child table for given fieldname'''
	rows = []
	if not df:
		df = self.meta.get_field(fieldname)

	for d in self.get(df.fieldname):
		if df.fieldname in ["requested_funds", "main_requested_funds", "return_requested_funds"]:
			if d.get("request_status") not in ["Approved", "Rejected"]:
				d.db_update()
		else:
			d.db_update()
		rows.append(d.name)

	if df.options in (self.flags.ignore_children_type or []):
		# do not delete rows for this because of flags
		# hack for docperm :(
		return

	child_table = frappe.qb.DocType(df.options)
	if rows:
		# select rows that do not match the ones in the document
		deleted_rows = (
			frappe.qb.from_(child_table)
			.select(child_table.name)
			.where(child_table.parent == self.name)
			.where(child_table.parenttype == self.doctype)
			.where(child_table.parentfield == fieldname)
			.where(child_table.name.notin(rows))
		).run()
		if len(deleted_rows) > 0:
			# delete rows that do not match the ones in the document
			frappe.qb.from_(child_table).delete().where(
				child_table.name.isin([row[0] for row in deleted_rows])
			).run()

	else:
		# no rows found, delete all rows
		(
			frappe.qb.from_(child_table)
			.delete()
			.where(child_table.parent == self.name)
			.where(child_table.parenttype == self.doctype)
			.where(child_table.parentfield == fieldname)
		).run()
