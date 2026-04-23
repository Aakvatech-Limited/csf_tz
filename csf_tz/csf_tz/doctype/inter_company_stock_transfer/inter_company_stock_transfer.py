# Copyright (c) 2023, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import erpnext
from erpnext.stock.stock_ledger import get_valuation_rate
from frappe.utils import flt

class InterCompanyStockTransfer(Document):
    def validate(self):
        allow_inter_company_stock_transfer = frappe.db.get_value("CSF TZ Settings", "CSF TZ Settings", "allow_inter_company_stock_transfer")
        if not allow_inter_company_stock_transfer:
            frappe.throw("<b><h4>Inter Company Stock Transfer is not enabled, please contact system administrator</h4></b>")
        if self.from_company == self.to_company:
            frappe.throw("From and To Company cannot be same")
        self._set_missing_basic_rates()


    def before_submit(self,warehouse=None):
        item_list_from, item_list_to = [], []
        self._set_missing_basic_rates(throw_if_missing=True)

        for item in self.items_child:
            valuation_rate = flt(item.get("basic_rate"))
            if not valuation_rate:
                frappe.throw(f"Valuation rate is zero or not found for Item {item.item_code} in warehouse {self.default_from_warehouse}")
            else:
                item_list_from.append({
                    "item_code": item.item_code,
                    "uom": item.uom,
                    "qty": item.qty,
                    "s_warehouse": self.default_from_warehouse,
                    "basic_rate": valuation_rate,
                    "batch_no": item.batch_no,
                })

                item_list_to.append({
                    "item_code": item.item_code,
                    "uom": item.uom,
                    "qty": item.qty,
                    "t_warehouse": self.default_to_warehouse,
                    "basic_rate": valuation_rate,
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

    def _set_missing_basic_rates(self, throw_if_missing=False):
        if not self.from_company or not self.default_from_warehouse:
            return

        for item in self.items_child:
            if not item.item_code or flt(item.basic_rate):
                continue

            valuation_rate = get_valuation_rate(
                item.item_code,
                self.default_from_warehouse,
                self.doctype,
                self.name,
                currency=erpnext.get_company_currency(self.from_company),
                company=self.from_company,
                raise_error_if_no_rate=False,
                batch_no=item.batch_no,
            )
            if valuation_rate:
                item.basic_rate = valuation_rate
            elif throw_if_missing:
                frappe.throw(
                    f"Valuation rate is zero or not found for Item {item.item_code} in warehouse {self.default_from_warehouse}"
                )
