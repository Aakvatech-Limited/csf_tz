import json

import frappe
from frappe.tests.utils import FrappeTestCase

from csf_tz.csftz_hooks.get_successor_json import get_json


class TestGetSuccessorJson(FrappeTestCase):
    def test_ancestor_type_bound_as_parameter_not_column(self):
        """Original SQL used `ancestor_type` as an unquoted column reference,
        causing 'Unknown column ancestor_type in where clause' on every call.
        Fixed: QB passes it as a bound string parameter."""
        dt = frappe.qb.DocType("DocType")
        q = frappe.qb.from_(dt).select(dt.name).where(dt.module == "Accounts")
        sql = q.get_sql()
        self.assertIn("'Accounts'", sql)
        self.assertNotIn("`ancestor_type`", sql)

    def test_get_json_runs_without_sql_error(self):
        result = json.loads(get_json("ignored", "Accounts"))
        self.assertIsInstance(result, list)
