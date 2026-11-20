import frappe
from frappe.tests.utils import FrappeTestCase


class TestTrialBalanceReportInUsd(FrappeTestCase):
    def test_set_gl_entries_by_account_called_with_v15_signature(self):
        """In v15 set_gl_entries_by_account moved min_lft/max_rgt to keyword
        args (root_lft, root_rgt) and inserted filters as positional arg 4.
        Calling with the old positional order silently passed min_lft as
        filters and filters as root_lft, producing wrong results. This test
        verifies the corrected call does not raise TypeError."""
        from erpnext.accounts.report.financial_statements import (
            set_gl_entries_by_account,
        )

        company = frappe.db.get_value("Company", {}, "name")
        if not company:
            return

        fiscal_year = frappe.db.get_value(
            "Fiscal Year", {}, ["year_start_date", "year_end_date"], as_dict=True
        )
        if not fiscal_year:
            return

        filters = frappe._dict(
            company=company,
            from_date=str(fiscal_year.year_start_date),
            to_date=str(fiscal_year.year_end_date),
            with_period_closing_entry=0,
        )
        # Must not raise TypeError from wrong positional argument order
        set_gl_entries_by_account(
            filters.company,
            filters.from_date,
            filters.to_date,
            filters,
            {},
            root_lft=1,
            root_rgt=99999,
            ignore_closing_entries=True,
        )

    def test_execute_returns_columns_and_data(self):
        """execute must return a (columns, data) tuple without raising."""
        from csf_tz.csf_tz.report.trial_balance_report_in_usd.trial_balance_report_in_usd import (
            execute,
        )

        company = frappe.db.get_value("Company", {}, "name")
        fiscal_year = frappe.db.get_value("Fiscal Year", {}, "name")
        if not company or not fiscal_year:
            return

        filters = frappe._dict(company=company, fiscal_year=fiscal_year)
        columns, data = execute(filters)
        self.assertIsInstance(columns, list)
        self.assertIsInstance(data, list)
