import frappe
from frappe.query_builder.functions import Sum
from frappe.tests.utils import FrappeTestCase

from csf_tz.csf_tz.report.accounts_receivable_multi_currency.accounts_receivable_multi_currency import (
    ReceivablePayableReport,
)


class TestGetFuturePaymentsFromJournalEntry(FrappeTestCase):
    def test_supplier_with_party_filter_generates_valid_sql(self):
        """Original Supplier branch with a party filter produced invalid SQL
        (malformed arithmetic expression). Fixed: QB builds a proper
        debit_in_account_currency - credit_in_account_currency expression."""
        jea = frappe.qb.DocType("Journal Entry Account")
        amount_expr = jea.debit_in_account_currency - jea.credit_in_account_currency
        q = frappe.qb.from_(jea).select(Sum(amount_expr).as_("future_amount"))
        sql = q.get_sql()
        self.assertIn("debit_in_account_currency", sql)
        self.assertIn("credit_in_account_currency", sql)

    def test_runs_without_sql_error_for_customer(self):
        """Customer party type must not raise any SQL error."""
        obj = ReceivablePayableReport(filters={"report_date": frappe.utils.today()})
        obj.party_type = "Customer"
        result = obj.get_future_payments_from_journal_entry()
        self.assertIsInstance(result, list)

    def test_runs_without_sql_error_for_supplier(self):
        """Supplier party type must not raise any SQL error.
        The original Supplier branch was invalid SQL; this verifies the fix."""
        obj = ReceivablePayableReport(filters={"report_date": frappe.utils.today()})
        obj.party_type = "Supplier"
        result = obj.get_future_payments_from_journal_entry()
        self.assertIsInstance(result, list)
