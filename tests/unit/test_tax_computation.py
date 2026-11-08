"""Standalone domain and service tests; no site/database is needed."""

import importlib.util
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = ROOT / "csf_tz/income_tax/rules.py"
spec = importlib.util.spec_from_file_location("tax_rules", RULES_PATH)
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)


class TaxRulesTests(unittest.TestCase):
	def test_effective_mapping_boundaries_and_gaps(self):
		mappings = [
			{"valid_from": "2026-01-01", "valid_to": "2026-06-30", "tax_category": "Old"},
			{"valid_from": "2026-07-01", "valid_to": None, "tax_category": "New"},
		]
		self.assertIsNone(rules.resolve_default(mappings, "2025-12-31"))
		self.assertEqual(rules.resolve_default(mappings, "2026-06-30"), "Old")
		self.assertEqual(rules.resolve_default(mappings, "2026-07-01"), "New")
		with self.assertRaises(ValueError):
			rules.resolve_default(mappings + [mappings[0]], "2026-01-01")

	def test_expense_split(self):
		rules.validate_allocations(100, [60, 40])

	def test_income_and_return_signs(self):
		rules.validate_allocations(-100, [-25, -75])
		rules.validate_allocations(100, [100])

	def test_currency_rounding(self):
		rules.validate_allocations(0.1 + 0.2, [0.1, 0.2])
		rules.validate_allocations(100.123, [50.111, 50.012], precision=3)

	def test_invalid_splits(self):
		for net, values in [
			(100, [99]),
			(100, [101]),
			(100, [120, -20]),
			(-100, [100]),
			(0, [0]),
			(100, []),
			(100, [0, 100]),
			(100, [float("nan")]),
		]:
			with self.subTest(net=net, values=values), self.assertRaises(ValueError):
				rules.validate_allocations(net, values)

	def test_fingerprint_detects_source_and_ledger_changes(self):
		gl = {"name": "GL-1", "debit": 100, "credit": 0, "voucher_detail_no": "ITEM-1"}
		baseline = rules.fingerprint(gl, "2026-11-08 10:00")
		self.assertEqual(baseline, rules.fingerprint(dict(gl), "2026-11-08 10:00"))
		for changed in [dict(gl, debit=101), dict(gl, is_cancelled=1), dict(gl, voucher_detail_no="ITEM-2")]:
			self.assertNotEqual(baseline, rules.fingerprint(changed, "2026-11-08 10:00"))
		self.assertNotEqual(baseline, rules.fingerprint(gl, "2026-11-08 11:00"))

	def test_approval_does_not_hide_missing_evidence_or_stale_sources(self):
		review = SimpleNamespace(source_fingerprint="a", docstatus=1, evidence_exception_reason=None)
		self.assertEqual(rules.review_status(None, "a", []), "Unreviewed")
		self.assertEqual(rules.review_status(review, "b", []), "Source Changed")
		self.assertEqual(rules.review_status(review, "a", ["Missing"]), "Evidence Required")
		review.evidence_exception_reason = "Replacement evidence requested"
		self.assertEqual(rules.review_status(review, "a", ["Missing"]), "Reviewed with Exception")
		review.docstatus = 0
		self.assertEqual(rules.review_status(review, "a", []), "Draft Review")
		review.docstatus = 1
		self.assertEqual(rules.review_status(review, "a", []), "Reviewed")


class TaxServiceTests(unittest.TestCase):
	def setUp(self):
		self.frappe = MagicMock()
		self.frappe._ = lambda text: text
		self.frappe.whitelist = lambda: lambda method: method

		def throw(message, *args, **kwargs):
			raise ValueError(message)

		self.frappe.throw.side_effect = throw
		utils = MagicMock()
		from datetime import date

		utils.getdate = lambda value: date.fromisoformat(str(value))
		utils.now_datetime.return_value = "NOW"
		spec = importlib.util.spec_from_file_location(
			"tax_service_test", ROOT / "csf_tz/income_tax/service.py"
		)
		self.service = importlib.util.module_from_spec(spec)
		with patch.dict(
			"sys.modules",
			{"frappe": self.frappe, "frappe.utils": utils, "csf_tz.income_tax.rules": rules},
		):
			spec.loader.exec_module(self.service)

	def test_source_requires_read_permissions_and_matching_company(self):
		gl = SimpleNamespace(
			is_cancelled=0,
			voucher_type="Purchase Invoice",
			voucher_no="PI-1",
			company="Company A",
			posting_date="2026-01-01",
			check_permission=MagicMock(),
		)
		mapping = SimpleNamespace(
			enabled=1,
			company_field="company",
			posting_date_field="posting_date",
			check_permission=MagicMock(),
		)
		source = MagicMock(docstatus=1)
		source.get.side_effect = lambda key: {"company": "Company B", "posting_date": "2026-01-01"}[key]
		self.frappe.get_doc.side_effect = [gl, mapping, source]
		with self.assertRaisesRegex(ValueError, "company do not match"):
			self.service.source_context("GL-1")
		gl.check_permission.assert_called_once_with("read")
		source.check_permission.assert_called_once_with("read")

	def test_source_cancellation_preserves_other_apps_link_exceptions(self):
		doc = MagicMock()
		doc.get.return_value = ["Other Audit Log"]
		self.service.allow_source_cancellation(doc)
		self.assertEqual(doc.ignore_linked_doctypes, ["Other Audit Log", "TZ Tax Transaction Review"])

	def test_cancelled_source_rejected(self):
		self.frappe.get_doc.return_value = SimpleNamespace(is_cancelled=1, check_permission=MagicMock())
		with self.assertRaisesRegex(ValueError, "Cancelled"):
			self.service.source_context("GL-1")

	def test_required_evidence_must_exist_and_cover_posting_date(self):
		self.frappe.get_cached_value.return_value = 1
		self.frappe.db.exists.return_value = True
		review = SimpleNamespace(
			allocations=[SimpleNamespace(tax_category="CSR")], posting_date="2026-01-01", evidence=[]
		)
		self.assertTrue(self.service.evidence_issues(review))
		review.evidence = [SimpleNamespace(attachment="/private/files/proof.pdf", valid_until="2025-12-31")]
		self.assertTrue(self.service.evidence_issues(review))
		review.evidence[0].valid_until = "2026-12-31"
		self.assertFalse(self.service.evidence_issues(review))
		self.frappe.db.exists.return_value = False
		self.assertTrue(self.service.evidence_issues(review))

	def test_approval_blocks_missing_evidence_and_unresolved_classification(self):
		review = SimpleNamespace(
			allocations=[SimpleNamespace(tax_category="CSR")], evidence_exception_reason=None
		)
		with patch.object(self.service, "evidence_issues", return_value=["Missing evidence"]):
			with self.assertRaisesRegex(ValueError, "Missing evidence"):
				self.service.approve_review(review)
		with patch.object(self.service, "evidence_issues", return_value=[]):
			self.frappe.get_cached_value.return_value = "Review Required"
			with self.assertRaisesRegex(ValueError, "Resolve"):
				self.service.approve_review(review)
			self.frappe.get_cached_value.return_value = "Restricted Deduction"
			self.service.approve_review(review)
			self.assertEqual(review.reviewed_by, self.frappe.session.user)
			self.assertEqual(review.reviewed_on, "NOW")


class TaxMetadataTests(unittest.TestCase):
	def test_all_new_doctypes_resolve_and_active_gl_key_is_unique(self):
		folder = ROOT / "csf_tz/income_tax/doctype"
		paths = list(folder.glob("tz_tax_*/*.json"))
		self.assertEqual(len(paths), 6)
		for path in paths:
			data = json.loads(path.read_text())
			self.assertEqual(data["module"], "Income Tax")
			self.assertEqual(set(data["field_order"]), {f["fieldname"] for f in data["fields"]})
			self.assertTrue(path.with_suffix(".py").exists())
			if data["name"] == "TZ Tax Transaction Review":
				self.assertTrue(
					next(f for f in data["fields"] if f["fieldname"] == "active_gl_entry")["unique"]
				)
				user = next(p for p in data["permissions"] if p["role"] == "Accounts User")
				self.assertFalse(user.get("submit"))
		self.assertIn("Income Tax", (ROOT / "csf_tz/modules.txt").read_text().splitlines())
		module = ROOT / "csf_tz/income_tax"
		report = json.loads(
			(module / "report/tz_tax_review_register/tz_tax_review_register.json").read_text()
		)
		self.assertEqual(report["module"], "Income Tax")
		workspace = json.loads((module / "workspace/income_tax/income_tax.json").read_text())
		sidebar = json.loads((module / "sidebar/income_tax/income_tax.json").read_text())
		self.assertEqual(workspace["module"], "Income Tax")
		self.assertEqual(sidebar["module"], "Income Tax")
		expected = {
			"TZ Tax Transaction Review",
			"TZ Tax Category",
			"TZ Tax Account Mapping",
			"TZ Tax Source Mapping",
			"TZ Tax Review Register",
		}
		self.assertEqual({item["link_to"] for item in workspace["links"] if item["type"] == "Link"}, expected)
		self.assertEqual({item["link_to"] for item in sidebar["items"] if item.get("child")}, expected)
		dock = json.loads((ROOT / "csf_tz/dock/csf_tz/csf_tz.json").read_text())
		self.assertEqual(sum(item["link_to"] == "Income Tax" for item in dock["items"]), 1)


if __name__ == "__main__":
	unittest.main()
