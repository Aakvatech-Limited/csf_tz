import frappe
from frappe.tests.utils import FrappeTestCase

from csf_tz.csf_tz.report.item_price_by_price_list.item_price_by_price_list import (
    build_bin_maps,
    build_price_map,
)


class TestItemPriceByPriceList(FrappeTestCase):
    def test_build_bin_maps_uses_weighted_stock_value_and_omits_zero_qty_warehouses(
        self,
    ):
        rows = [
            frappe._dict(
                item_code="ITEM-001",
                warehouse="WH-A",
                actual_qty=2,
                valuation_rate=100,
            ),
            frappe._dict(
                item_code="ITEM-001",
                warehouse="WH-B",
                actual_qty=3,
                valuation_rate=200,
            ),
            frappe._dict(
                item_code="ITEM-001",
                warehouse="WH-ZERO",
                actual_qty=0,
                valuation_rate=999,
            ),
        ]

        qty_map, value_map, warehouse_map = build_bin_maps(rows)

        self.assertEqual(qty_map["ITEM-001"], 5)
        self.assertEqual(value_map["ITEM-001"], 800)
        self.assertEqual(
            warehouse_map["ITEM-001"],
            ["WH-A - 2.0", "WH-B - 3.0"],
        )

    def test_build_price_map_keeps_latest_current_generic_stock_uom_price(self):
        rows = [
            frappe._dict(
                item_code="ITEM-001",
                price_list="Standard Selling",
                price_list_rate=100,
                uom="Nos",
                valid_from="2026-01-01",
                valid_upto=None,
                customer=None,
                supplier=None,
                batch_no=None,
            ),
            frappe._dict(
                item_code="ITEM-001",
                price_list="Standard Selling",
                price_list_rate=120,
                uom="Nos",
                valid_from="2026-02-01",
                valid_upto=None,
                customer=None,
                supplier=None,
                batch_no=None,
            ),
            frappe._dict(
                item_code="ITEM-001",
                price_list="Standard Selling",
                price_list_rate=999,
                uom="Nos",
                valid_from="2026-01-01",
                valid_upto=None,
                customer="CUSTOMER-001",
                supplier=None,
                batch_no=None,
            ),
            frappe._dict(
                item_code="ITEM-001",
                price_list="Standard Selling",
                price_list_rate=888,
                uom="Box",
                valid_from="2026-01-01",
                valid_upto=None,
                customer=None,
                supplier=None,
                batch_no=None,
            ),
        ]

        price_map = build_price_map(
            rows,
            {"ITEM-001": "Nos"},
            as_on_date="2026-10-06",
        )

        self.assertEqual(price_map[("ITEM-001", "Standard Selling")], 120)
