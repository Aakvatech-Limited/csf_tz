# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []
	columns = [
		{"fieldname": "name", "label": _("Purchase Order"), "fieldtype": "Link", "options": "Purchase Order"},
		{
			"fieldname": "transaction_date",
			"label": _("Date"),
			"fieldtype": "Date",
		},
		{
			"fieldname": "req_by",
			"label": _("Req By Date"),
			"fieldtype": "Date",
		},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
		},
		{"fieldname": "supplier_name", "label": _("Supplier Name"), "fieldtype": "Data", "width": 150},
		{"fieldname": "project", "label": _("Project"), "fieldtype": "Data", "width": 150},
		{
			"fieldname": "item_code",
			"label": _("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
		},
		{"fieldname": "qty", "label": _("Qty"), "fieldtype": "Float", "width": 150},
		{"fieldname": "received_qty", "label": _("Received Qty"), "fieldtype": "Float", "width": 150},
		{"fieldname": "qty_to_receive", "label": _("Qty To Receive"), "fieldtype": "Float", "width": 150},
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 150,
		},
		{"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 150},
		{"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 200},
		{"fieldname": "brand", "label": _("Brand"), "fieldtype": "Data", "width": 100},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 150,
		},
	]
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	where_filter = {
		"from_date": filters.from_date,
		"to_date": filters.to_date,
	}
	where = ""
	if filters.purchase_order:
		where += "  AND tpo.name = %(purchase_order)s "
		where_filter.update({"purchase_order": filters.purchase_order})
	if filters.item_code:
		where += "  AND tpoi.item_code = %(item_code)s "
		where_filter.update({"item_code": filters.item_code})
	if filters.warehouse:
		where += "  AND tpoi.warehouse = %(warehouse)s "
		where_filter.update({"warehouse": filters.warehouse})
	if filters.supplier:
		where += "  AND tpo.supplier = %(supplier)s "
		where_filter.update({"supplier": filters.supplier})

	data = frappe.db.sql(
		"""SELECT
								tpo.name ,
								tpo.transaction_date ,
								tpoi.schedule_date AS req_by,
								tpo.supplier,
								tpo.supplier_name,
								tpoi.project,
								tpoi.item_code,
								tpoi.qty ,
								tpoi.received_qty,
								(tpoi.qty - ifnull(tpoi.received_qty, 0)) AS qty_to_receive,
							    tpoi.warehouse,
								tpoi.item_name,
								tpoi.description,
							    tpoi.brand,
								tpo.company
							FROM
								(`tabPurchase Order` tpo), (`tabPurchase Order Item` tpoi)
							/*LEFT JOIN
								(`tabPurchase Order Item` tpoi) ON (tpoi.parent = tpo.name)*/
							WHERE
								tpoi.parent = tpo.name
							and tpo.docstatus = 1
							and tpo.status not in ("Stopped", "Closed")
							and ifnull(tpoi.received_qty, 0) < ifnull(tpoi.qty, 0)
							AND tpo.transaction_date BETWEEN %(from_date)s AND %(to_date)s
/*							ORDER BY tpo.transaction_date
*/							"""
		+ where,
		where_filter,
		as_dict=1,
		as_list=1,
	)
	return columns, data
