"""Safety checks for folding vfd_providers into csf_tz.

A v15 site carries both apps. After the v16 upgrade the VFD doctypes are shipped by
csf_tz, while vfd_providers may stay installed or be uninstalled at any time. These
tests cover the module ownership, hook registration and settings backfill that decide
whether that upgrade keeps the fiscal receipt history intact.
"""

import os
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from csf_tz.patches import migrate_vfd_providers_to_csf_tz
from csf_tz.vfd_support import upgrade
from csf_tz.vfd_support import utils as vfd_utils

VFD_MODULES = ("VFD Providers", "VFD Settings")

VFD_DOCTYPES = (
	"VFD Provider",
	"VFD Provider Attribute",
	"VFD Provider Posting",
	"VFDPlus Settings",
	"Simplify VFD Settings",
	"Total VFD Setting",
	"Company VFD Provider",
)

SETTINGS_DOCTYPES = ("VFDPlus Settings", "Simplify VFD Settings", "Total VFD Setting")

RETIRED_APP = "vfd_providers"


def declared_modules(app):
	path = os.path.join(frappe.get_app_path(app), "modules.txt")
	if not os.path.exists(path):
		return []
	with open(path) as modules_file:
		return [line.strip() for line in modules_file if line.strip()]


def doctypes_dropped_by_uninstalling(app):
	"""The doctypes frappe.installer.remove_app would drop for this app."""
	modules = frappe.get_all("Module Def", filters={"app_name": app}, pluck="name")
	if not modules:
		return set()
	return set(frappe.get_all("DocType", filters={"module": ["in", modules]}, pluck="name"))


def hook_targets(hook_name):
	"""Every handler path registered under a doc_events style hook, across installed apps."""
	targets = []
	for doctype_events in (frappe.get_hooks(hook_name) or {}).values():
		for handlers in doctype_events.values() if isinstance(doctype_events, dict) else []:
			targets.extend(handlers if isinstance(handlers, list) else [handlers])
	return targets


class TestVFDModuleOwnership(IntegrationTestCase):
	def test_vfd_modules_are_owned_by_csf_tz(self):
		for module in VFD_MODULES:
			self.assertEqual(
				frappe.db.get_value("Module Def", module, "app_name"),
				"csf_tz",
				f"{module} must be owned by csf_tz or uninstalling vfd_providers drops its tables",
			)

	def test_only_one_installed_app_declares_the_vfd_modules(self):
		for module in VFD_MODULES:
			owners = [app for app in frappe.get_installed_apps() if module in declared_modules(app)]
			self.assertEqual(owners, ["csf_tz"], f"{module} is declared by {owners}")

	def test_module_app_map_resolves_vfd_modules_to_csf_tz(self):
		from frappe.modules.utils import get_module_app

		for module in VFD_MODULES:
			self.assertEqual(get_module_app(module), "csf_tz")

	def test_migrated_doctypes_are_shipped_on_disk_by_csf_tz(self):
		for doctype in VFD_DOCTYPES:
			module = frappe.db.get_value("DocType", doctype, "module")
			path = os.path.join(
				frappe.get_app_path("csf_tz"),
				frappe.scrub(module),
				"doctype",
				frappe.scrub(doctype),
				f"{frappe.scrub(doctype)}.json",
			)
			self.assertTrue(os.path.exists(path), f"csf_tz ships no schema for {doctype} at {path}")

	def test_shipped_schema_matches_the_live_table(self):
		"""Every field csf_tz ships must exist in the table, so no stored value is orphaned."""
		for doctype in VFD_DOCTYPES:
			meta = frappe.get_meta(doctype)
			if meta.issingle:
				continue
			columns = set(frappe.db.get_table_columns(doctype))
			for field in meta.fields:
				if field.fieldtype in frappe.model.no_value_fields:
					continue
				self.assertIn(field.fieldname, columns, f"{doctype}.{field.fieldname} has no column")


class TestVFDUninstallSafety(IntegrationTestCase):
	def test_uninstalling_vfd_providers_drops_no_vfd_doctype(self):
		at_risk = doctypes_dropped_by_uninstalling(RETIRED_APP) & set(VFD_DOCTYPES)
		self.assertEqual(at_risk, set(), f"uninstalling {RETIRED_APP} would drop {sorted(at_risk)}")

	def test_uninstall_before_migrate_would_drop_the_vfd_tables(self):
		"""Locks in the migration patch as the only thing standing between an upgrade and data loss."""
		for module in VFD_MODULES:
			frappe.db.set_value("Module Def", module, "app_name", RETIRED_APP, update_modified=False)

		unmigrated = doctypes_dropped_by_uninstalling(RETIRED_APP) & set(VFD_DOCTYPES)
		self.assertEqual(unmigrated, set(VFD_DOCTYPES), "expected the pre-migrate state to be unsafe")

		migrate_vfd_providers_to_csf_tz.execute()
		self.assertEqual(doctypes_dropped_by_uninstalling(RETIRED_APP) & set(VFD_DOCTYPES), set())

	def test_vfd_custom_fields_are_not_linked_to_a_module(self):
		"""Custom Field.module is a Module Def link, so a module deletion would cascade to it."""
		linked = frappe.get_all(
			"Custom Field",
			filters={"fieldname": ["like", "vfd_%"], "module": ["in", VFD_MODULES]},
			fields=["dt", "fieldname", "module"],
		)
		self.assertEqual(linked, [], f"these fields die with the module: {linked}")

	def test_no_sales_invoice_vfd_column_is_orphaned(self):
		"""A vfd_* column with no field definition holds data the site can no longer read."""
		defined = {field.fieldname for field in frappe.get_meta("Sales Invoice").fields}
		orphans = [
			column
			for column in frappe.db.get_table_columns("Sales Invoice")
			if column.startswith(("vfd_", "is_not_vfd", "is_auto_generate_vfd")) and column not in defined
		]
		self.assertEqual(orphans, [], f"unreadable Sales Invoice columns: {orphans}")


class TestVFDHookRegistration(IntegrationTestCase):
	def test_vfd_providers_registers_no_own_hooks(self):
		"""Left installed, the old app must not fire a second copy of the VFD handlers."""
		for hook in ("doc_events", "scheduler_events", "doctype_js", "override_doctype_class"):
			self.assertFalse(
				frappe.get_hooks(hook, app_name=RETIRED_APP),
				f"{RETIRED_APP} still registers {hook}",
			)

	def test_fiscalisation_runs_exactly_once_per_submit(self):
		on_submit = frappe.get_hooks("doc_events").get("Sales Invoice", {}).get("on_submit", [])
		autogenerate = [handler for handler in on_submit if handler.endswith("autogenerate_vfd")]
		self.assertEqual(
			autogenerate,
			["csf_tz.vfd_support.utils.autogenerate_vfd"],
			"a duplicate handler sends the same invoice to TRA twice",
		)

	def test_no_installed_app_still_points_at_vfd_providers_code(self):
		stale = [target for target in hook_targets("doc_events") if target.startswith("vfd_providers.")]
		self.assertEqual(stale, [], f"handlers that break once vfd_providers is removed: {stale}")

	def test_vfd_retry_job_is_scheduled_once(self):
		crons = frappe.get_hooks("scheduler_events").get("cron", {})
		posting = [
			target
			for targets in crons.values()
			for target in targets
			if target.endswith("posting_all_vfd_invoices")
		]
		self.assertEqual(len(posting), 1, f"the VFD retry job is scheduled {len(posting)} times: {posting}")


class TestMissingVFDStartDate(IntegrationTestCase):
	"""vfd_start_date is new and mandatory, and only the client may decide the value.

	Invoices raised before the client moved onto this system were fiscalised elsewhere, so a
	guessed date would either re-send them or silently exclude real ones. The upgrade therefore
	leaves the field empty and has to say so loudly.
	"""

	def company(self):
		name = frappe.get_all("Company", pluck="name", limit=1)
		if name:
			return name[0]
		if not frappe.db.exists("Warehouse Type", "Transit"):
			frappe.get_doc(doctype="Warehouse Type", name="Transit").insert()
		company = frappe.get_doc(
			doctype="Company",
			company_name="VFD Audit Co",
			abbr="VAC",
			default_currency="TZS",
			country="Tanzania",
		).insert()
		return company.name

	def settings_row(self, doctype, company, start_date=None, **values):
		"""VFDPlus Settings.validate calls TRA over the network, so stub that out."""
		with patch(
			"csf_tz.vfd_providers.doctype.vfdplus_settings.vfdplus_settings.send_vfdplus_request",
			return_value={},
		):
			if not frappe.db.exists(doctype, company):
				frappe.get_doc(doctype=doctype, company=company, **values).insert(ignore_mandatory=True)
			elif values:
				frappe.db.set_value(doctype, company, values, update_modified=False)
		frappe.db.set_value(doctype, company, "vfd_start_date", start_date, update_modified=False)
		return company

	def configure_provider(self, settings_doctype, company):
		provider = {"VFDPlus Settings": "VFDPlus", "Total VFD Setting": "TotalVFD"}.get(
			settings_doctype, "SimplifyVFD"
		)
		if not frappe.db.exists("VFD Provider", provider):
			frappe.get_doc(
				doctype="VFD Provider", vfd_provider=provider, vfd_provider_settings=settings_doctype
			).insert()
		if not frappe.db.exists("Company VFD Provider", company):
			frappe.get_doc(doctype="Company VFD Provider", company=company, vfd_provider=provider).insert()
		frappe.clear_cache()
		return provider

	def test_migrate_never_invents_a_start_date(self):
		company = self.company()
		self.settings_row("VFDPlus Settings", company, start_date=None, gov_reg_sdate="2021-07-01")

		for hook in frappe.get_hooks("after_migrate", app_name="csf_tz"):
			frappe.get_attr(hook)()

		self.assertIsNone(
			frappe.db.get_value("VFDPlus Settings", company, "vfd_start_date"),
			"the upgrade must leave VFD Start Date for the client to decide",
		)

	def test_retry_job_reports_a_company_without_a_start_date(self):
		company = self.company()
		settings_doctype = "VFDPlus Settings"
		self.configure_provider(settings_doctype, company)
		self.settings_row(settings_doctype, company, start_date=None)

		with (
			patch.object(vfd_utils, "vfdplus_post_fiscal_receipt") as post,
			patch.object(frappe, "log_error") as log_error,
		):
			vfd_utils.posting_all_vfd_invoices()

		self.assertFalse(post.called, "an invoice must not be sent before a start date is set")
		self.assertTrue(log_error.called, "the company was skipped with no post and no log")
		self.assertIn(settings_doctype, log_error.call_args.kwargs["message"])

	def test_generating_vfd_without_a_start_date_names_the_settings_to_fix(self):
		company = self.company()
		settings_doctype = "VFDPlus Settings"
		self.configure_provider(settings_doctype, company)
		self.settings_row(settings_doctype, company, start_date=None)

		invoice = frappe._dict(
			name="SINV-VFD-TEST",
			company=company,
			posting_date=today(),
			is_not_vfd_invoice=0,
			is_return=0,
			vfd_status="Not Sent",
		)
		self.assertRaisesRegex(
			frappe.ValidationError,
			settings_doctype,
			vfd_utils.generate_tra_vfd,
			docname=invoice.name,
			sinv_doc=invoice,
		)


class TestStaleVFDProvidersGuard(IntegrationTestCase):
	"""An old vfd_providers keeps its own copies of the handlers csf_tz now owns."""

	def test_migrate_is_allowed_when_the_retired_app_registers_nothing(self):
		upgrade.block_stale_vfd_providers()

	def test_migrate_is_blocked_when_the_retired_app_still_hooks_sales_invoice(self):
		stale = {"Sales Invoice": {"on_submit": ["vfd_providers.utils.utils.autogenerate_vfd"]}}

		with (
			patch.object(frappe, "get_installed_apps", return_value=["csf_tz", RETIRED_APP]),
			patch.object(
				frappe, "get_hooks", side_effect=lambda hook, **kw: stale if hook == "doc_events" else {}
			),
		):
			self.assertRaisesRegex(frappe.ValidationError, "twice", upgrade.block_stale_vfd_providers)


class TestVFDUninstallHandover(IntegrationTestCase):
	"""vfd_providers hands the modules to csf_tz instead of dropping their tables."""

	def setUp(self):
		if RETIRED_APP not in frappe.get_installed_apps():
			self.skipTest(f"{RETIRED_APP} is not installed on this site")
		from vfd_providers import uninstall

		self.uninstall = uninstall

	def claim_modules_for_the_retired_app(self):
		for module in VFD_MODULES:
			frappe.db.set_value("Module Def", module, "app_name", RETIRED_APP, update_modified=False)

	def test_before_uninstall_hands_the_modules_to_csf_tz(self):
		self.claim_modules_for_the_retired_app()

		self.uninstall.before_uninstall()

		self.assertEqual(doctypes_dropped_by_uninstalling(RETIRED_APP) & set(VFD_DOCTYPES), set())
		for module in VFD_MODULES:
			self.assertEqual(frappe.db.get_value("Module Def", module, "app_name"), "csf_tz")

	def test_before_uninstall_refuses_to_drop_populated_modules(self):
		self.claim_modules_for_the_retired_app()
		if not frappe.db.exists("VFD Provider", "VFDPlus"):
			frappe.get_doc(
				doctype="VFD Provider", vfd_provider="VFDPlus", vfd_provider_settings="VFDPlus Settings"
			).insert()

		with patch.object(self.uninstall, "is_successor_installed", return_value=False):
			self.assertRaisesRegex(
				frappe.ValidationError, "csf_tz is not installed", self.uninstall.before_uninstall
			)

	def test_before_uninstall_allows_removal_when_the_modules_are_empty(self):
		self.claim_modules_for_the_retired_app()
		for doctype in VFD_DOCTYPES:
			frappe.db.delete(doctype)

		with patch.object(self.uninstall, "is_successor_installed", return_value=False):
			self.uninstall.before_uninstall()


class TestVFDPrintFormats(IntegrationTestCase):
	FORMATS = ("AV TI VFD", "SI POS Inv")

	def test_standard_vfd_print_formats_are_shipped_by_an_installed_app(self):
		for name in self.FORMATS:
			row = frappe.db.get_value("Print Format", name, ["module", "standard"], as_dict=True)
			if not row or row.standard != "Yes":
				continue
			app = frappe.db.get_value("Module Def", row.module, "app_name")
			self.assertIn(
				app,
				frappe.get_installed_apps(),
				f"print format {name} is owned by {app}, which is not installed",
			)
			path = os.path.join(
				frappe.get_app_path(app),
				frappe.scrub(row.module),
				"print_format",
				frappe.scrub(name),
				f"{frappe.scrub(name)}.json",
			)
			self.assertTrue(os.path.exists(path), f"{name} has no shipped definition at {path}")
