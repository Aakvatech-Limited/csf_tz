import frappe
from frappe.tests.utils import FrappeTestCase

from csf_tz.clearing_and_forwarding.report.bond_report.bond_report import execute


def _filters(**overrides):
	f = frappe._dict(
		from_date="2026-01-01",
		to_date="2026-01-31",
		filter_by="Bond Date",
		status="Not Cancelled",
		bt=None,
	)
	f.update(overrides)
	return f


class TestBondReport(FrappeTestCase):
	def test_no_filters_raises(self):
		with self.assertRaises(frappe.ValidationError):
			execute(None)

	def test_missing_from_date_raises(self):
		with self.assertRaises(frappe.ValidationError):
			execute(_filters(from_date=None))

	def test_missing_to_date_raises(self):
		with self.assertRaises(frappe.ValidationError):
			execute(_filters(to_date=None))

	def test_inverted_date_range_raises(self):
		with self.assertRaises(frappe.ValidationError):
			execute(_filters(from_date="2026-02-01", to_date="2026-01-01"))

	def test_missing_filter_by_raises(self):
		with self.assertRaises(frappe.ValidationError):
			execute(_filters(filter_by=None))

	def test_unknown_filter_by_raises(self):
		with self.assertRaises(frappe.ValidationError):
			execute(_filters(filter_by="Posting Date"))

	def test_bond_cancelation_date_filter_by_is_accepted(self):
		columns, data = execute(_filters(filter_by="Bond Cancelation Date"))
		self.assertIsInstance(columns, list)
		self.assertIsInstance(data, list)

	def test_valid_filters_return_columns_and_list(self):
		columns, data = execute(_filters())
		self.assertIsInstance(columns, list)
		self.assertGreater(len(columns), 0)
		self.assertIsInstance(data, list)
