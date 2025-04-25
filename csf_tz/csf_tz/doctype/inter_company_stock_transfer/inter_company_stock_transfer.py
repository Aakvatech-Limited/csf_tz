# Copyright (c) 2023, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.stock.get_item_details import get_valuation_rate

class InterCompanyStockTransfer(Document):
    def before_submit(self,warehouse=None):
        item_list_from, item_list_to = [], []

        for item in self.items_child:
            
            valuation_rate_data = get_valuation_rate(item.item_code, self.from_company, self.default_from_warehouse)
            if not valuation_rate_data or valuation_rate_data.valuation_rate is None or valuation_rate_data.valuation_rate == 0:
                frappe.throw(f"Valuation rate is zero or not found for Item {item.item_code} in warehouse {self.default_from_warehouse}")
            else:
                item_list_from.append({
                    "item_name": item.item_name,
                    "item_code": item.item_code,
                    "uom": item.uom,
                    "qty": item.qty,
                    "s_warehouse": self.default_from_warehouse,
                    "basic_rate": valuation_rate_data.valuation_rate,
                    "batch_no": item.batch_no,
                })

                item_list_to.append({
                    "item_name": item.item_name,
                    "item_code": item.item_code,
                    "uom": item.uom,
                    "qty": item.qty,
                    "t_warehouse": self.default_to_warehouse,
                    "basic_rate": valuation_rate_data.valuation_rate,
                    "batch_no": item.batch_no,
                    "cost_center": ""
                })
        entry_from = frappe.get_doc({
            "doctype": "Stock Entry",
            "company": self.from_company,
            "stock_entry_type": "From Company",
            "from_warehouse": self.default_from_warehouse,
            "items": item_list_from,
            "transfer_goods_between_company": self.name
        })
        entry_from.insert(ignore_permissions=True)
        entry_from.submit()

        entry_to = frappe.get_doc({
            "doctype": "Stock Entry",
            "company": self.to_company,
            "stock_entry_type": "To Company",
            "to_warehouse": self.default_to_warehouse,
            "items": item_list_to,
            "transfer_goods_between_company": self.name
        })
        entry_to.insert(ignore_permissions=True)
        entry_to.submit()

        self.material_issue = entry_from.name
        self.material_receipt = entry_to.name
