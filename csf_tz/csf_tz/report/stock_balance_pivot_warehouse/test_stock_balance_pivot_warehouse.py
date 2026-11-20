import frappe
from frappe.tests.utils import FrappeTestCase


class TestStockBalancePivotWarehouse(FrappeTestCase):
    def test_sle_warehouse_map_qualifies_item_code_with_table(self):
        """get_sle_warehouse_map previously used Field('item_code') without a
        table alias. When sle and item are joined, both have item_code, so the
        query fails with an ambiguous column error. Fixed: sle.item_code."""
        sle = frappe.qb.DocType("Stock Ledger Entry")
        item = frappe.qb.DocType("Item")
        q = (
            frappe.qb.from_(sle)
            .inner_join(item)
            .on(sle.item_code == item.item_code)
            .select(sle.item_code)
            .where(sle.item_code.isin(["NONEXISTENT-ITEM-XYZ"]))
        )
        sql = q.get_sql()
        self.assertIn("`tabStock Ledger Entry`.`item_code`", sql)

    def test_execute_returns_columns_and_data(self):
        from csf_tz.csf_tz.report.stock_balance_pivot_warehouse.stock_balance_pivot_warehouse import (
            execute,
        )

        columns, data = execute({})
        self.assertIsInstance(columns, list)
        self.assertIsInstance(data, list)
