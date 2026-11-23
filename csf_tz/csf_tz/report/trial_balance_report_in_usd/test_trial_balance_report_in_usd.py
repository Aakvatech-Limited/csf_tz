# Tests for get_dimension_conditions in trial_balance_report_in_usd
import unittest

import frappe


class TestGetDimensionConditions(unittest.TestCase):
	def setUp(self):
		from csf_tz.csf_tz.report.trial_balance_report_in_usd.trial_balance_report_in_usd import (
			get_dimension_conditions,
		)

		self.get_dimension_conditions = get_dimension_conditions
		self.gl_entry = frappe.qb.DocType("GL Entry")

	def _get_sql(self, filters, dimension_field):
		"""Return the SQL fragment generated for a given filter dict."""
		from frappe.query_builder import Criterion

		conds = self.get_dimension_conditions(filters, self.gl_entry)
		if not conds:
			return ""
		q = frappe.qb.from_(self.gl_entry).select(self.gl_entry.name).where(Criterion.all(conds))
		return q.get_sql()

	def test_single_string_value_uses_isin(self):
		# A single string must be wrapped so .isin() gets a list, not chars
		sql = self._get_sql({"branch": "HQ"}, "branch")
		self.assertIn("'HQ'", sql)
		self.assertNotIn("'H'", sql)
		self.assertNotIn("'Q'", sql)

	def test_two_values_uses_isin(self):
		sql = self._get_sql({"branch": ["HQ", "Mwanza"]}, "branch")
		self.assertIn("'HQ'", sql)
		self.assertIn("'Mwanza'", sql)

	def test_three_values_uses_isin(self):
		sql = self._get_sql({"branch": ["HQ", "Mwanza", "Arusha"]}, "branch")
		self.assertIn("'HQ'", sql)
		self.assertIn("'Mwanza'", sql)
		self.assertIn("'Arusha'", sql)

	def test_no_value_returns_no_conditions(self):
		conds = self.get_dimension_conditions({}, self.gl_entry)
		self.assertEqual(conds, [])
