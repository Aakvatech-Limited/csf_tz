# Tests for filter validation in monthly_timesheet_report
import unittest

import frappe


class TestMonthlyTimesheetValidation(unittest.TestCase):
    def setUp(self):
        from csf_tz.csf_tz.report.monthly_timesheet_report.monthly_timesheet_report import (
            validate_filters,
        )

        self.validate_filters = validate_filters

    def test_missing_filters_raises(self):
        with self.assertRaises(frappe.ValidationError):
            self.validate_filters(None)

    def test_missing_from_date_raises(self):
        with self.assertRaises(frappe.ValidationError):
            self.validate_filters(frappe._dict({"to_date": "2024-12-31"}))

    def test_missing_to_date_raises(self):
        with self.assertRaises(frappe.ValidationError):
            self.validate_filters(frappe._dict({"from_date": "2024-01-01"}))

    def test_valid_filters_do_not_raise(self):
        # Should not raise
        self.validate_filters(
            frappe._dict({"from_date": "2024-01-01", "to_date": "2024-12-31"})
        )
