from __future__ import annotations

import json
from pathlib import Path

import frappe


SETUP_SPECS = (
	{
		"file": "accounts.json",
		"doctype": "Account",
		"identity_fields": ("account_name", "company"),
	},
	{
		"file": "leave_types.json",
		"doctype": "Leave Type",
		"identity_fields": ("leave_type_name",),
	},
	{
		"file": "salary_components.json",
		"doctype": "Salary Component",
		"identity_fields": ("salary_component",),
	},
	{
		"file": "sales_taxes_and_charges_templates.json",
		"doctype": "Sales Taxes and Charges Template",
		"identity_fields": ("title", "company"),
	},
	{
		"file": "purchase_taxes_and_charges_templates.json",
		"doctype": "Purchase Taxes and Charges Template",
		"identity_fields": ("title", "company"),
	},
	{
		"file": "item_tax_templates.json",
		"doctype": "Item Tax Template",
		"identity_fields": ("title", "company"),
	},
	{
		"file": "leave_policies.json",
		"doctype": "Leave Policy",
		"identity_fields": ("title",),
		"submit_after_insert": True,
	},
	{
		"file": "salary_structures.json",
		"doctype": "Salary Structure",
		"identity_fields": ("name",),
	},
)
TOKENS = {
	"{company}": lambda company, _abbr: company,
	"{abbr}": lambda _company, abbr: abbr,
}
ACCOUNT_LINK_FIELDS = {"parent_account", "account", "account_head", "tax_type", "payment_account"}
COST_CENTER_LINK_FIELDS = {"cost_center"}


def execute():
	company = get_target_company()
	if not company:
		frappe.logger().info(
			"Skipping csf_tz setup: no Company on the site yet. "
			"Re-run csf_tz.utils.setup.execute after a Company is created."
		)
		return

	abbr = frappe.get_cached_value("Company", company, "abbr")
	if not abbr:
		frappe.logger().info(f"Skipping csf_tz setup: Company {company} has no abbreviation.")
		return

	currency = frappe.get_cached_value("Company", company, "default_currency")
	if currency != "TZS":
		frappe.logger().info(
			f"Skipping csf_tz setup install for Company {company}: "
			f"default_currency is {currency!r}, not 'TZS'."
		)
		return

	for spec in SETUP_SPECS:
		if not frappe.db.exists("DocType", spec["doctype"]):
			continue

		for record in load_records(spec["file"]):
			doc = render_record(record, company, abbr)
			doc = resolve_links(doc, company, abbr)
			existing_name = get_existing_name(spec["doctype"], doc, spec["identity_fields"])
			if existing_name:
				submit_if_needed(spec, existing_name)
				continue

			doc["docstatus"] = 0
			inserted = frappe.get_doc(doc)
			inserted.insert(ignore_permissions=True, ignore_if_duplicate=True)
			submit_if_needed(spec, inserted.name)


def get_target_company() -> str | None:
	default_company = frappe.db.get_single_value("Global Defaults", "default_company")
	if default_company:
		return default_company

	companies = frappe.get_all("Company", pluck="name", order_by="creation asc", limit=1)
	return companies[0] if companies else None


def load_records(file_name: str) -> list[dict]:
	file_path = Path(__file__).resolve().parent.parent / "setup_data" / file_name
	with file_path.open() as handle:
		return json.load(handle)


def render_record(value, company: str, abbr: str):
	if isinstance(value, dict):
		return {key: render_record(item, company, abbr) for key, item in value.items()}

	if isinstance(value, list):
		return [render_record(item, company, abbr) for item in value]

	if isinstance(value, str):
		for token, resolver in TOKENS.items():
			value = value.replace(token, resolver(company, abbr))
		return value

	return value


def resolve_links(value, company: str, abbr: str):
	if isinstance(value, dict):
		resolved = {}
		for key, item in value.items():
			item = resolve_links(item, company, abbr)
			if isinstance(item, str) and key in ACCOUNT_LINK_FIELDS:
				item = resolve_account(item, company, abbr)
			elif isinstance(item, str) and key in COST_CENTER_LINK_FIELDS:
				item = resolve_cost_center(item, company, abbr)
			resolved[key] = item
		return resolved

	if isinstance(value, list):
		return [resolve_links(item, company, abbr) for item in value]

	return value


def resolve_account(value: str, company: str, abbr: str) -> str:
	if frappe.db.exists("Account", value):
		return value

	account_name = strip_company_suffix(value, abbr)
	return frappe.db.get_value("Account", {"account_name": account_name, "company": company}, "name") or value


def resolve_cost_center(value: str, company: str, abbr: str) -> str:
	if frappe.db.exists("Cost Center", value):
		return value

	cost_center_name = strip_company_suffix(value, abbr)
	return (
		frappe.db.get_value("Cost Center", {"cost_center_name": cost_center_name, "company": company}, "name")
		or value
	)


def strip_company_suffix(value: str, abbr: str) -> str:
	suffix = f" - {abbr}"
	if value.endswith(suffix):
		return value[: -len(suffix)]
	return value


def get_existing_name(doctype: str, doc: dict, identity_fields: tuple[str, ...]) -> str | None:
	filters = {field: doc[field] for field in identity_fields if doc.get(field) is not None}
	if not filters:
		return None

	return frappe.db.get_value(doctype, filters, "name", order_by="creation asc")


def submit_if_needed(spec: dict, name: str):
	if not spec.get("submit_after_insert") or not frappe.db.exists(spec["doctype"], name):
		return

	doc = frappe.get_doc(spec["doctype"], name)
	if doc.docstatus == 0:
		doc.flags.ignore_permissions = True
		doc.submit()
