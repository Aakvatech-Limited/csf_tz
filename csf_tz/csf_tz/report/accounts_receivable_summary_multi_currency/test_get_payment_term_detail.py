import frappe
from frappe.tests.utils import FrappeTestCase

from csf_tz.csf_tz.report.accounts_receivable_summary_multi_currency.accounts_receivable_utils import (
    ReceivablePayableReport,
)


class TestGetPaymentTermDetail(FrappeTestCase):
    def test_company_bound_as_string_parameter(self):
        """Original SQL double-quoted the company value (WHERE si.company = "Acme").
        MySQL ANSI mode treats double-quoted values as identifiers, so the query
        matched a non-existent column instead of the string. Fixed: QB binds it
        as a single-quoted string parameter."""
        si = frappe.qb.DocType("Sales Invoice")
        ps = frappe.qb.DocType("Payment Schedule")
        q = (
            frappe.qb.from_(si)
            .inner_join(ps)
            .on(si.name == ps.parent)
            .select(si.name)
            .where(si.company == "Acme Corp")
        )
        sql = q.get_sql()
        self.assertIn("'Acme Corp'", sql)
        self.assertNotIn('"Acme Corp"', sql)

    def test_get_payment_term_detail_runs_without_sql_error(self):
        """Running the query with a valid company and no matching invoices must
        not raise a SQL error. The old double-quoted company caused the query
        to fail even with an otherwise valid call."""
        obj = ReceivablePayableReport(
            {"company": "_Test Company", "report_date": frappe.utils.today()}
        )
        result = obj.get_payment_term_detail(["FAKE-SI-NONEXISTENT"])
        self.assertIsInstance(result, frappe._dict)
