import frappe
from frappe.tests.utils import FrappeTestCase


class TestWarehouseWiseItemBalanceAndValue(FrappeTestCase):
    def test_execute_raises_not_ported_error(self):
        """The report was written against ERPNext v14 APIs that were removed in v15
        (get_item_details, get_item_warehouse_map, get_fifo_queue as module-level
        functions; six.iteritems). The stub raises frappe.ValidationError until
        the report is ported."""
        from csf_tz.csf_tz.report.warehouse_wise_item_balance_and_value.warehouse_wise_item_balance_and_value import (
            execute,
        )

        with self.assertRaises(frappe.ValidationError):
            execute({})

    def test_module_imports_without_error(self):
        """The broken v15 imports must not appear at module level. Importing
        the module must not raise ImportError."""
        import csf_tz.csf_tz.report.warehouse_wise_item_balance_and_value.warehouse_wise_item_balance_and_value  # noqa: F401
