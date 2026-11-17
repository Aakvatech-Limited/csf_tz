# -*- coding: utf-8 -*-
# Copyright (c) 2017, Bravo Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import time
import datetime
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import Field
from frappe.query_builder.functions import Sum

class RequestedItems(Document):
	def onload(self):
		self.set_approval_status()
		self.set_issue_status()
		
				
	def set_approval_status(self):
		waiting_approval = frappe.db.get_values('Requested Items Table', 
				{"parent": self.get('reference_docname'), "parenttype": self.get('reference_doctype'), "parentfield": 'requested_items', "status": ["not in", ['Approved', 'Rejected']]})
		
		if waiting_approval and self.approval_status != "Waiting Approval":
			self.db_set('approval_status', 'Waiting Approval')
		elif not waiting_approval and self.approval_status != "Processed":
			self.db_set('approval_status', 'Processed')
		frappe.db.commit()
		
		
	def set_issue_status(self):
		waiting_issue = False
		fully_issued = True
		issued_qty = 0

		requested_items_table = frappe.qb.DocType("Requested Items Table")
		children_approved = (
			frappe.qb.from_(requested_items_table)
			.select(requested_items_table.item, Sum(requested_items_table.quantity).as_("quantity"))
			.where(requested_items_table.parenttype == self.get('reference_doctype'))
			.where(requested_items_table.parent == self.get('reference_docname'))
			.where(requested_items_table.parentfield == 'requested_items')
			.where(requested_items_table.status == 'Approved')
			.groupby(requested_items_table.item)
		).run(as_dict=True)
			
		stock_entry_detail = frappe.qb.DocType("Stock Entry Detail")
		stock_entries = self.get_stock_entries_query()
		for row in children_approved:
			issued = (
				frappe.qb.from_(stock_entry_detail)
				.select(Sum(stock_entry_detail.qty).as_("issued_qty"))
				.where(stock_entry_detail.item_code == row.item)
				.where(stock_entry_detail.parenttype == 'Stock Entry')
				.where(stock_entry_detail.parent.isin(stock_entries))
			).run(as_dict=True)
				
			
			if not issued[0].issued_qty:
				self.db_set('items_issue_status', 'To Issue')
				frappe.db.commit()
			elif issued[0].issued_qty and issued[0].issued_qty < row.quantity and self.items_issue_status != 'To Issue': #If partially issued
				fully_issued = False
				issued_qty = issued_qty + issued[0].issued_qty
				self.db_set('items_issue_status', 'To Issue')
				frappe.db.commit()
		
		#If fully issued	
		if fully_issued and issued_qty > 0 and self.items_issue_status not in ['Waiting Approval', 'Fully Issued']:
			self.db_set('items_issue_status', 'Fully Issued')
			frappe.db.commit()
			
		
	def get_stock_entries_query(self):
		stock_entry = frappe.qb.DocType("Stock Entry")
		return (
			frappe.qb.from_(stock_entry)
			.select(stock_entry.name)
			.where(stock_entry.reference_doctype == 'Requested Items')
			.where(stock_entry.reference_docname == self.name)
		)

	def get_all_children(self, parenttype=None):
		#For getting children
		return []
		
	def update_children(self):
		'''update child tables'''
		self.update_child_table([])
		
	def load_from_db(self):
		"""Load document and children from database and create properties
		from fields"""
		if not getattr(self, "_metaclass", False) and self.meta.issingle:
			single_doc = frappe.db.get_singles_dict(self.doctype)
			if not single_doc:
				single_doc = frappe.new_doc(self.doctype).as_dict()
				single_doc["name"] = self.doctype
				del single_doc["__islocal"]

			super(Document, self).__init__(single_doc)
			self.init_valid_columns()
			self._fix_numeric_types()

		else:
			d = frappe.db.get_value(self.doctype, self.name, "*", as_dict=1)
			if not d:
				frappe.throw(_("{0} {1} not found").format(_(self.doctype), self.name), frappe.DoesNotExistError)

			super(Document, self).__init__(d)

		if self.name=="DocType" and self.doctype=="DocType":
			from frappe.model.meta import doctype_table_fields
			table_fields = doctype_table_fields
		else:
			table_fields = self.meta.get_table_fields()

		for df in table_fields:
			if df.fieldname == "previous_requested_items": 
				#Load approved or rejected requests
				children_approved = frappe.db.get_values(df.options,
					{"parent": self.get('reference_docname'), "parenttype": self.get('reference_doctype'), "parentfield": 'requested_items', "status": "Approved"},
					"*", as_dict=True, order_by="idx asc")
				children_rejected = frappe.db.get_values(df.options,
					{"parent": self.get('reference_docname'), "parenttype": self.get('reference_doctype'), "parentfield": 'requested_items', "status": "Rejected"},
					"*", as_dict=True, order_by="idx asc")
				children = children_approved + children_rejected
				if children:
					self.set(df.fieldname, children)
				else:
					self.set(df.fieldname, [])
			elif df.fieldname == "requested_items": 
				#Load requests which are not approved nor rejected
				children = frappe.db.get_values(df.options,
					{"parent": self.get('reference_docname'), "parenttype": self.get('reference_doctype'), "parentfield": 'requested_items', "status": "Requested"},
					"*", as_dict=True, order_by="idx asc")
				children += frappe.db.get_values(df.options,
					{"parent": self.get('reference_docname'), "parenttype": self.get('reference_doctype'), "parentfield": 'requested_items', "status": "Recommended"},
					"*", as_dict=True, order_by="idx asc")
				children += frappe.db.get_values(df.options,
					{"parent": self.get('reference_docname'), "parenttype": self.get('reference_doctype'), "parentfield": 'requested_items', "status": "Recommended Against"},
					"*", as_dict=True, order_by="idx asc")
				if children:
					self.set(df.fieldname, children)
				else:
					self.set(df.fieldname, [])
			elif df.fieldname == "issued_items":
				#Load previously issued items
				stock_entry_detail = frappe.qb.DocType("Stock Entry Detail")
				requested_items_table = frappe.qb.DocType("Requested Items Table")
				children = (
					frappe.qb.from_(stock_entry_detail)
					.left_join(requested_items_table)
					.on(
						(requested_items_table.item == stock_entry_detail.item_code)
						& (requested_items_table.status == 'Approved')
						& (requested_items_table.parenttype == self.get('reference_doctype'))
						& (requested_items_table.parent == self.get('reference_docname'))
					)
					.select(
						stock_entry_detail.item_code.as_("item"),
						Sum(requested_items_table.quantity).as_("requested"),
						Sum(stock_entry_detail.qty).as_("issued"),
						(Sum(requested_items_table.quantity) - Sum(stock_entry_detail.qty)).as_("difference"),
						stock_entry_detail.uom.as_("units"),
					)
					.where(stock_entry_detail.parenttype == 'Stock Entry')
					.where(stock_entry_detail.parent.isin(self.get_stock_entries_query()))
					.groupby(Field("item"), Field("units"))
				).run(as_dict=True)
				if children:
					self.set(df.fieldname, children)
				else:
					self.set(df.fieldname, [])

		# sometimes __setup__ can depend on child values, hence calling again at the end
		if hasattr(self, "__setup__"):
			self.__setup__()
	
@frappe.whitelist(allow_guest=True)
def request_items(**args):
	args = frappe._dict(args)
	
	existing_payment_request = frappe.db.get_value("Requested Items", 
		{"reference_doctype": args.reference_doctype, "reference_docname": args.reference_docname})
	
	#Timestamp
	ts = time.time()
	timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
		
	if existing_payment_request:
		#Mark the request as open
		doc = frappe.get_doc("Requested Items", existing_payment_request)
		doc.db_set("approval_status", "Waiting Approval")
		doc.db_set("modified", timestamp)
		return "Request Updated"
	else:
		request = frappe.new_doc("Requested Items")
		request.update({
			"reference_doctype":args.reference_doctype,
			"reference_docname": args.reference_docname
		})
		request.insert(ignore_permissions=True)
		return "Request Inserted"
		

@frappe.whitelist(allow_guest=True)
def recommend_request(**args):
	args = frappe._dict(args)
	
	#Timestamp
	ts = time.time()
	timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
	
	doc = frappe.get_doc("Requested Items Table", args.request_docname)
	doc.db_set("status", "Recommended")
	doc.db_set("recommended_by", args.user)
	doc.db_set("recommended_date", timestamp)
	return "Request Updated"

	
@frappe.whitelist(allow_guest=True)
def recommend_against_request(**args):
	args = frappe._dict(args)
	
	#Timestamp
	ts = time.time()
	timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
	
	doc = frappe.get_doc("Requested Items Table", args.request_docname)
	doc.db_set("status", "Recommended Against")
	doc.db_set("recommended_by", args.user)
	doc.db_set("recommended_date", timestamp)
	return "Request Updated"


@frappe.whitelist(allow_guest=True)
def approve_request(**args):
	args = frappe._dict(args)
	
	#Timestamp
	ts = time.time()
	timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
	
	doc = frappe.get_doc("Requested Items Table", args.request_docname)
	doc.db_set("status", "Approved")
	doc.db_set("approved_by", args.user)
	doc.db_set("approved_date", timestamp)
	return "Request Updated"
	
@frappe.whitelist(allow_guest=True)
def reject_request(**args):
	args = frappe._dict(args)
	
	#Timestamp
	ts = time.time()
	timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
	
	doc = frappe.get_doc("Requested Items Table", args.request_docname)
	doc.db_set("status", "Rejected")
	doc.db_set("approved_by", args.user)
	doc.db_set("approved_date", timestamp)
	return "Request Updated"
	
@frappe.whitelist()
def make_from_requested_items(source_name, target_doc=None, ignore_permissions=False):
	def postprocess(source, target):
		set_missing_values(source, target)
		
	def set_missing_values(source, target):
		target.purpose = "Material Issue"
	
	doclist = get_mapped_doc("Requested Items", source_name, {
		"Requested Items": {
			"doctype": "Stock Entry",
			"field_map": {
				"doctype": "reference_doctype",
				"name": "reference_docname"
			}
		}
	}, target_doc, postprocess)

	return doclist
