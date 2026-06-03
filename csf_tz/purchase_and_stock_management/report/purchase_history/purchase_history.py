# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []
	columns = [
		{
			"fieldname": "item_code",
			"label": _("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
		},
		{"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 150},
		{
			"fieldname": "item_group",
			"label": _("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
		},
		{"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 200},
		{"fieldname": "qty", "label": _("Qty"), "fieldtype": "Float", "width": 150},
		{"fieldname": "uom", "label": _("UOM"), "fieldtype": "Link", "options": "UOM", "width": 80},
		{"fieldname": "base_rate", "label": _("Rate"), "fieldtype": "Currency", "width": 80},
		{"fieldname": "base_amount", "label": _("Amount"), "fieldtype": "Currency", "width": 80},
		{"fieldname": "name", "label": _("Purchase Order"), "fieldtype": "Link", "options": "Purchase Order"},
		{
			"fieldname": "transaction_date",
			"label": _("Date"),
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
		{"fieldname": "received_qty", "label": _("Received Qty"), "fieldtype": "Float", "width": 150},
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
		where += "  AND po_item.item_code = %(item_code)s "
		where_filter.update({"item_code": filters.item_code})
	if filters.supplier:
		where += "  AND tpo.supplier = %(supplier)s "
		where_filter.update({"supplier": filters.supplier})

	data = frappe.db.sql(
		"""SELECT
								po_item.item_code,
								po_item.item_name,
								po_item.item_group,
								po_item.description,
								po_item.qty ,
								po_item.uom,
								po_item.base_rate,
								po_item.base_amount,

								tpo.name ,
								tpo.transaction_date ,
								tpo.supplier,
								sup.supplier_name,
								po_item.project,
								ifnull(po_item.received_qty, 0) AS received_qty,
								tpo.company

							FROM
								(`tabPurchase Order` tpo), (`tabPurchase Order Item` po_item), (`tabSupplier` sup)
							/*LEFT JOIN
								(`tabPurchase Order Item` po_item) ON (po_item.parent = tpo.name)*/
							WHERE
								po_item.parent = tpo.name
							AND tpo.supplier = sup.name
							AND tpo.transaction_date BETWEEN %(from_date)s AND %(to_date)s
							AND tpo.docstatus = 1 """
		+ where,
		where_filter,
		as_dict=1,
		as_list=1,
	)
	return columns, data
