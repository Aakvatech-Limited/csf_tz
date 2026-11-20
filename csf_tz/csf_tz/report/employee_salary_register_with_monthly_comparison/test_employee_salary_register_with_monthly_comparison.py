import frappe
from frappe.tests.utils import FrappeTestCase

from csf_tz.csf_tz.report.employee_salary_register_with_monthly_comparison.employee_salary_register_with_monthly_comparison import (
    validate_filters,
)


class TestEmployeeSalaryRegisterWithMonthlyComparison(FrappeTestCase):
    def test_validate_filters_raises_when_docstatus_missing(self):
        with self.assertRaises(frappe.ValidationError):
            validate_filters({})

    def test_validate_filters_raises_when_filters_is_none(self):
        with self.assertRaises(frappe.ValidationError):
            validate_filters(None)

    def test_validate_filters_passes_when_docstatus_present(self):
        validate_filters({"docstatus": "Submitted"})
