# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.stock.get_item_details import get_valuation_rate


class InterCompanyMaterialRequest(Document):
        def before_submit(self,warehouse=None):
            
            if self.from_company == self.to_company:
                frappe.throw("From and To Company cannot be same") 
                
            item_list = []

            for item in self.items_child:
                
                valuation_rate_data = get_valuation_rate(item.item_code, self.from_company, self.default_from_warehouse)
                if not valuation_rate_data or valuation_rate_data.valuation_rate is None or valuation_rate_data.valuation_rate == 0:
                    frappe.throw(f"Valuation rate is zero or not found for Item {item.item_code} in warehouse {self.default_from_warehouse}")
                else:
                    item_list.append({
                        "item_name": item.item_name,
                        "item_code": item.item_code,
                        "uom": item.uom,
                        "qty": item.qty,
                        "s_warehouse": self.default_from_warehouse,
                        "t_warehouse": self.default_to_warehouse,
                        "basic_rate": valuation_rate_data.valuation_rate,
                        "batch_no": item.batch_no,
                    })
            
            # Create Inter Company Stock Transfer

            request = frappe.get_doc({
                "doctype": "Inter Company Stock Transfer",
                "from_company": self.from_company,
                "to_company": self.to_company,
                "default_from_warehouse": self.default_from_warehouse,
                "default_to_warehouse": self.default_to_warehouse,
                "items_child": item_list,
                "transfer_goods_between_company": self.name
            })
            request.insert(ignore_permissions=True)
            request.save()
            
            self.inter_company_stock_transfer = request.name