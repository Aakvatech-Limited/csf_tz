# Tests for filter validation and return type in price_change_history
import unittest

import frappe


class TestPriceChangeHistory(unittest.TestCase):
    def setUp(self):
        from csf_tz.csf_tz.report.price_change_history.price_change_history import (
            execute,
        )

        self.execute = execute

    def test_missing_company_raises(self):
        with self.assertRaises(frappe.ValidationError):
            self.execute({})

    def test_none_filters_raises(self):
        with self.assertRaises(frappe.ValidationError):
            self.execute(None)

    def test_returns_tuple_of_two(self):
        # execute must always return (columns, data) even on empty data
        result = self.execute(frappe._dict({"company": "__test_nonexistent__"}))
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        columns, data = result
        self.assertIsInstance(columns, list)
        self.assertIsInstance(data, list)
