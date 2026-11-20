import frappe
from frappe.tests.utils import FrappeTestCase

from csf_tz.csf_tz.report.salary_register_summary.salary_register_summary import (
    validate_filters,
)


class TestSalaryRegisterSummary(FrappeTestCase):
    def test_validate_filters_raises_when_docstatus_missing(self):
        with self.assertRaises(frappe.ValidationError):
            validate_filters({})

    def test_validate_filters_raises_when_filters_is_none(self):
        with self.assertRaises(frappe.ValidationError):
            validate_filters(None)

    def test_validate_filters_passes_when_docstatus_present(self):
        validate_filters({"docstatus": "Submitted"})
