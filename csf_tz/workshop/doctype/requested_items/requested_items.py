# -*- coding: utf-8 -*-
# Copyright (c) 2017, Bravo Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import time
import datetime
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

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
		
		
	def set_issue_status(self):
		waiting_issue = False
		fully_issued = True
		issued_qty = 0

		children_approved = frappe.db.sql('''SELECT item, SUM(quantity) AS quantity FROM `tabRequested Items Table` WHERE \
				parenttype = %(reference_doctype)s \
				AND parent = %(reference_docname)s \
				AND parentfield = 'requested_items' \
				AND status = 'Approved' 
				GROUP BY item''', {'reference_doctype': self.get('reference_doctype'), 'reference_docname': self.get('reference_docname')}, as_dict=True)
			
		for row in children_approved:
			issued = frappe.db.sql('''SELECT SUM(`tabStock Entry Detail`.qty) AS issued_qty FROM `tabStock Entry Detail` \
				WHERE \
				`tabStock Entry Detail`.item_code = %(item)s \
				AND `tabStock Entry Detail`.parenttype = 'Stock Entry' \
				AND `tabStock Entry Detail`.parent IN \
				(SELECT name FROM `tabStock Entry` WHERE `tabStock Entry`.reference_doctype = 'Requested Items' AND `tabStock Entry`.reference_docname = %(docname)s)''', 
				{'docname': self.name, 'item': row.item}, as_dict=True)
				
			
			if not issued[0].issued_qty:
				self.db_set('items_issue_status', 'To Issue')
			elif issued[0].issued_qty and issued[0].issued_qty < row.quantity and self.items_issue_status != 'To Issue': #If partially issued
				fully_issued = False
				issued_qty = issued_qty + issued[0].issued_qty
				self.db_set('items_issue_status', 'To Issue')
		
		#If fully issued	
		if fully_issued and issued_qty > 0 and self.items_issue_status not in ['Waiting Approval', 'Fully Issued']:
			self.db_set('items_issue_status', 'Fully Issued')
			
		
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
				children = frappe.db.sql('''SELECT 
												`tabStock Entry Detail`.item_code AS item, 
												SUM(`tabRequested Items Table`.quantity) AS requested,
												SUM(`tabStock Entry Detail`.qty) AS issued,
												(SUM(`tabRequested Items Table`.quantity) - SUM(`tabStock Entry Detail`.qty)) AS difference,
												`tabStock Entry Detail`.uom AS units
											FROM \
												`tabStock Entry Detail` \
											LEFT JOIN \
												`tabRequested Items Table` ON `tabRequested Items Table`.item = `tabStock Entry Detail`.item_code \
												AND `tabRequested Items Table`.status = 'Approved'
												AND `tabRequested Items Table`.parenttype = %(reference_doctype)s \
												AND `tabRequested Items Table`.parent = %(reference_docname)s \
											WHERE \
												`tabStock Entry Detail`.parenttype = 'Stock Entry' \
												AND `tabStock Entry Detail`.parent IN \
													(SELECT name FROM `tabStock Entry` WHERE `tabStock Entry`.reference_doctype = 'Requested Items' AND `tabStock Entry`.reference_docname = %(docname)s)
											GROUP BY
												item, units''', {'docname': self.name, 'reference_docname': self.get('reference_docname'), 'reference_doctype': self.get('reference_doctype')} ,as_dict=1)
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
