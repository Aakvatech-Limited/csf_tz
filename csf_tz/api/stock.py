from __future__ import unicode_literals
import frappe
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry


def validate_with_material_request(self):
    bypass_material_request_validation = frappe.get_value("Company", self.company,"bypass_material_request_validation") or 0
    if bypass_material_request_validation:
        return
    for item in self.get("items"):
        if item.material_request:
            mreq_item = frappe.db.get_value("Material Request Item",
                {"name": item.material_request_item, "parent": item.material_request},
                ["item_code", "warehouse", "idx"], as_dict=True)
            if mreq_item.item_code != item.item_code or \
            mreq_item.warehouse != (item.s_warehouse if self.purpose== "Material Issue" else item.t_warehouse):
                frappe.throw(_("Item or Warehouse for row {0} does not match Material Request").format(item.idx),
                    frappe.MappingMismatchError)


def validate_with_material_request_override(doc, method):
    StockEntry.validate_with_material_request = validate_with_material_request

def import_from_bom(self, method):
    if self.stock_entry_type == "Manufacture" and self.bom_no:
        bom = frappe.get_doc("BOM", self.bom_no)
        for d in bom.additional_costs:
            self.append("additional_costs", {
                "expense_account": d.expense_account,
                "amount": d.cost_per_unit,
                "base_amount": d.cost_per_unit,
                "description": d.cost_type
            })
