# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []
	columns = [
		{
			"fieldname": "name",
			"label": _("Material Request"),
			"fieldtype": "Link",
			"options": "Material Request",
		},
		{
			"fieldname": "transaction_date",
			"label": _("Date"),
			"fieldtype": "Date",
		},
		{
			"fieldname": "item_code",
			"label": _("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
		},
		{"fieldname": "qty", "label": _("Qty"), "fieldtype": "Float", "width": 150},
		{"fieldname": "ordered_qty", "label": _("Ordered Qty"), "fieldtype": "Float", "width": 150},
		{"fieldname": "qty_to_order", "label": _("Qty To Order"), "fieldtype": "Float", "width": 150},
		{"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 150},
		{"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 150},
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
	if filters.material_request:
		where += "  AND tmr.name = %(material_request)s "
		where_filter.update({"material_request": filters.material_request})
	if filters.item_code:
		where += "  AND tmri.item_code = %(item_code)s "
		where_filter.update({"item_code": filters.item_code})

	data = frappe.db.sql(
		"""SELECT
								tmr.name ,
								tmr.transaction_date ,
								tmr.company,
								tmri.item_code,
								sum(ifnull(tmri.qty, 0)) AS qty,
								sum(ifnull(tmri.ordered_qty, 0)) AS ordered_qty,
								(sum(tmri.qty) - sum(ifnull(tmri.ordered_qty, 0))) AS qty_to_order,
								tmri.item_name,
								tmri.description,
								tmr.company
							FROM
								(`tabMaterial Request` tmr), (`tabMaterial Request Item` tmri)
							WHERE
								tmri.parent = tmr.name
							AND	tmr.material_request_type = "Purchase"
							AND tmr.docstatus = 1
							AND tmr.status != "Stopped"
							AND tmr.transaction_date BETWEEN %(from_date)s AND %(to_date)s
							GROUP BY tmr.name, tmri.item_code
							HAVING
								sum(ifnull(tmri.ordered_qty, 0)) < sum(ifnull(tmri.qty, 0))
/*							ORDER BY tmr.transaction_date
*/							"""
		+ where,
		where_filter,
		as_dict=1,
		as_list=1,
	)
	return columns, data
