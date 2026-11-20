# Tests for get_dimension_conditions in multi_currency_ledger
import unittest

import frappe


class TestMultiCurrencyLedgerDimensions(unittest.TestCase):
    def setUp(self):
        from csf_tz.csf_tz.report.multi_currency_ledger.multi_currency_ledger import (
            get_dimension_conditions,
        )

        self.get_dimension_conditions = get_dimension_conditions
        self.gl_entry = frappe.qb.DocType("GL Entry")

    def _get_sql(self, filters):
        from frappe.query_builder import Criterion

        conds = self.get_dimension_conditions(filters, self.gl_entry)
        if not conds:
            return ""
        q = (
            frappe.qb.from_(self.gl_entry)
            .select(self.gl_entry.name)
            .where(Criterion.all(conds))
        )
        return q.get_sql()

    def test_single_string_wrapped_not_iterated(self):
        # "HQ" must not be iterated as ['H', 'Q']
        sql = self._get_sql({"branch": "HQ"})
        self.assertIn("'HQ'", sql)
        self.assertNotIn("'H'", sql)

    def test_two_values(self):
        sql = self._get_sql({"branch": ["HQ", "Mwanza"]})
        self.assertIn("'HQ'", sql)
        self.assertIn("'Mwanza'", sql)

    def test_three_values(self):
        sql = self._get_sql({"branch": ["HQ", "Mwanza", "Arusha"]})
        self.assertIn("'HQ'", sql)
        self.assertIn("'Mwanza'", sql)
        self.assertIn("'Arusha'", sql)

    def test_empty_filters_produces_no_conditions(self):
        conds = self.get_dimension_conditions({}, self.gl_entry)
        self.assertEqual(conds, [])
