# -*- coding: utf-8 -*-
# Copyright (c) 2021, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now


class WorkOrderConsignment(Document):
    def before_submit(self):
        create_orders(self)


@frappe.whitelist()
def get_boms(item):
    boms = frappe.get_all("BOM", filters={
        "docstatus": 1,
        "is_active": 1,
        "transfer_material_against": "Work Order",
        "parent_item": item,
    })
    return boms


def create_orders(doc):
    for row in doc.work_order_consignment_detail:
        if row.bom:
            crate_work_order(row.bom, doc)


def crate_work_order(bom_name, doc):
    bom = frappe.get_doc("BOM", bom_name)
    wo_order = frappe.new_doc("Work Order")
    wo_order.production_item = bom.item
    wo_order.bom_no = bom_name
    wo_order.qty = doc.quantity
    wo_order.source_warehouse = doc.default_source_warehouse
    wo_order.wip_warehouse = bom.wip_warehouse
    wo_order.fg_warehouse = bom.fg_warehouse
    wo_order.scrap_warehouse = bom.scrap_warehouse
    wo_order.company = doc.company
    wo_order.stock_uom = bom.uom
    wo_order.use_multi_level_bom = 0
    wo_order.skip_transfer = 0
    wo_order.get_items_and_operations_from_bom()
    wo_order.planned_start_date = now()
    wo_order.parent_item = doc.parent_item
    wo_order.work_order_consignment = doc.name

    if bom.source_warehouse:
        for item in wo_order.get("required_items"):
            item.source_warehouse = bom.source_warehouse

    wo_order.insert(ignore_permissions=True)
    # wo_order.submit()

    frappe.msgprint(_("Work Order created: {0}").format(
        wo_order.name), alert=True)

    return wo_order.name
