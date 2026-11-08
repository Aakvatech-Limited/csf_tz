import frappe
from frappe import _
from frappe.utils import getdate

from csf_tz.income_tax.rules import fingerprint, resolve_default, review_status
from csf_tz.income_tax.service import GL_FIELDS, evidence_issues


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.company or not filters.from_date or not filters.to_date:
		frappe.throw(_("Company, From Date and To Date are required."))
	if getdate(filters.to_date) < getdate(filters.from_date):
		frappe.throw(_("To Date cannot precede From Date."))
	frappe.has_permission("TZ Tax Transaction Review", "read", throw=True)
	frappe.get_doc("Company", filters.company).check_permission("read")
	gl_filters = {
		"company": filters.company,
		"posting_date": ["between", [filters.from_date, filters.to_date]],
		"is_cancelled": 0,
		"voucher_type": ["!=", "Period Closing Voucher"],
	}
	if filters.account:
		gl_filters["account"] = filters.account
	if filters.source_doctype:
		gl_filters["voucher_type"] = filters.source_doctype
	accounts = {
		a.name: a
		for a in frappe.get_list(
			"Account", filters={"company": filters.company}, fields=["name", "report_type"], page_length=0
		)
	}
	reviews = {
		r.gl_entry: r.name
		for r in frappe.get_list(
			"TZ Tax Transaction Review",
			filters={
				"company": filters.company,
				"posting_date": ["between", [filters.from_date, filters.to_date]],
				"docstatus": ["!=", 2],
			},
			fields=["name", "gl_entry"],
			page_length=0,
		)
	}
	mappings = set(
		frappe.get_list(
			"TZ Tax Source Mapping", filters={"enabled": 1}, pluck="reference_doctype", page_length=0
		)
	)
	account_mappings = {}
	for row in frappe.get_list(
		"TZ Tax Account Mapping",
		filters={"company": filters.company, "enabled": 1},
		fields=["account", "tax_category", "valid_from", "valid_to"],
		page_length=0,
	):
		account_mappings.setdefault(row.account, []).append(row)
	disabled_categories = set(
		frappe.get_list("TZ Tax Category", filters={"disabled": 1}, pluck="name", page_length=0)
	)
	data, sources, seen = [], {}, set()
	start = 0
	while True:
		entries = frappe.get_list(
			"GL Entry",
			filters=gl_filters,
			fields=GL_FIELDS,
			order_by="posting_date, name",
			start=start,
			page_length=500,
		)
		if not entries:
			break
		start += len(entries)
		for gl in entries:
			seen.add(gl.name)
			if not gl.debit - gl.credit:
				continue
			if gl.account not in accounts:
				continue
			if not filters.include_balance_sheet and accounts[gl.account].report_type != "Profit and Loss":
				continue
			key = (gl.voucher_type, gl.voucher_no)
			if key not in sources:
				source = frappe.get_doc(*key)
				sources[key] = source if frappe.has_permission(source.doctype, "read", doc=source) else None
			source = sources[key]
			if source is None:
				continue
			review = None
			if gl.name in reviews:
				candidate = frappe.get_doc("TZ Tax Transaction Review", reviews[gl.name])
				if frappe.has_permission(candidate.doctype, "read", doc=candidate):
					review = candidate
			issues = evidence_issues(review) if review else []
			status = review_status(review, fingerprint(gl, source.modified), issues)
			if source.docstatus != 1:
				status = "Source Changed"
			if gl.voucher_type not in mappings:
				status = "Source Mapping Required"
			if filters.exceptions_only and status == "Reviewed":
				continue
			try:
				default = resolve_default(account_mappings.get(gl.account, []), gl.posting_date)
			except ValueError as exc:
				frappe.throw(str(exc))
			if default in disabled_categories:
				default = None
			allocations = list(review.allocations) if review else [None]
			for row in allocations:
				data.append(
					{
						"posting_date": gl.posting_date,
						"account": gl.account,
						"source_doctype": gl.voucher_type,
						"source_name": gl.voucher_no,
						"gl_entry": gl.name,
						"source_detail": gl.voucher_detail_no,
						"review": review.name if review else None,
						"status": status,
						"tax_category": row.tax_category if row else default,
						"amount": row.amount if row else gl.debit - gl.credit,
						"currency": frappe.get_cached_value("Company", gl.company, "default_currency"),
						"classification_source": "Transaction Review"
						if row
						else ("Account Default" if default else "Unmapped"),
						"evidence_issue": " ".join(issues),
						"evidence_exception_reason": review.evidence_exception_reason if review else None,
					}
				)
	# Retain review exceptions when a cancellation/repost removes the original GL row.
	for gl_name, review_name in reviews.items():
		if gl_name in seen:
			continue
		review = frappe.get_doc("TZ Tax Transaction Review", review_name)
		if not frappe.has_permission(review.doctype, "read", doc=review):
			continue
		if filters.account and review.account != filters.account:
			continue
		if filters.source_doctype and review.source_doctype != filters.source_doctype:
			continue
		account = accounts.get(review.account)
		if not account or (not filters.include_balance_sheet and account.report_type != "Profit and Loss"):
			continue
		original_gl = frappe.db.get_value("GL Entry", gl_name, ["name", "is_cancelled"], as_dict=True)
		status = "GL Entry Replaced"
		if original_gl:
			status = "Source Cancelled" if original_gl.is_cancelled else "Source Changed"
		for row in review.allocations:
			data.append(
				{
					"posting_date": review.posting_date,
					"account": review.account,
					"source_doctype": review.source_doctype,
					"source_name": review.source_name,
					"review": review.name,
					"status": status,
					"tax_category": row.tax_category,
					"amount": row.amount,
					"currency": review.currency,
					"classification_source": "Historical Review - Exclude from Current Ledger",
					"evidence_issue": _(
						"Original ledger entry is no longer active. Review the replacement posting."
					),
				}
			)
	return get_columns(), data


def get_columns():
	return [
		{"fieldname": "posting_date", "label": _("Posting Date"), "fieldtype": "Date", "width": 100},
		{
			"fieldname": "account",
			"label": _("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 210,
		},
		{"fieldname": "source_doctype", "label": _("Voucher Type"), "width": 140},
		{
			"fieldname": "source_name",
			"label": _("Voucher"),
			"fieldtype": "Dynamic Link",
			"options": "source_doctype",
			"width": 180,
		},
		{
			"fieldname": "gl_entry",
			"label": _("GL Entry"),
			"fieldtype": "Link",
			"options": "GL Entry",
			"width": 150,
		},
		{"fieldname": "source_detail", "label": _("Source Row ID"), "width": 140},
		{
			"fieldname": "tax_category",
			"label": _("Tax Category"),
			"fieldtype": "Link",
			"options": "TZ Tax Category",
			"width": 220,
		},
		{
			"fieldname": "amount",
			"label": _("Allocated Net (Debit - Credit)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 180,
		},
		{"fieldname": "currency", "label": _("Currency"), "width": 80},
		{"fieldname": "classification_source", "label": _("Classification Source"), "width": 150},
		{"fieldname": "status", "label": _("Review Status"), "width": 170},
		{
			"fieldname": "review",
			"label": _("Tax Review"),
			"fieldtype": "Link",
			"options": "TZ Tax Transaction Review",
			"width": 150,
		},
		{"fieldname": "evidence_issue", "label": _("Evidence Issue"), "width": 250},
		{"fieldname": "evidence_exception_reason", "label": _("Evidence Exception Reason"), "width": 250},
	]
