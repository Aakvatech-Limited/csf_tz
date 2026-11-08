"""Read accounting sources and maintain independent income-tax review extensions."""

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime

from csf_tz.tax_computation.rules import fingerprint, validate_allocations

GL_FIELDS = [
	"name",
	"company",
	"posting_date",
	"account",
	"debit",
	"credit",
	"voucher_type",
	"voucher_no",
	"voucher_detail_no",
	"is_cancelled",
]


def source_context(gl_name):
	gl = frappe.get_doc("GL Entry", gl_name)
	gl.check_permission("read")
	if gl.is_cancelled or gl.voucher_type == "Period Closing Voucher":
		frappe.throw(_("Cancelled and period-closing entries cannot be reviewed."))
	mapping = frappe.get_doc("TZ Tax Source Mapping", gl.voucher_type)
	mapping.check_permission("read")
	if not mapping.enabled:
		frappe.throw(_("Tax source mapping is disabled."))
	source = frappe.get_doc(gl.voucher_type, gl.voucher_no)
	source.check_permission("read")
	if source.docstatus != 1:
		frappe.throw(_("Only submitted accounting sources can be reviewed."))
	if source.get(mapping.company_field) != gl.company:
		frappe.throw(_("Source and GL Entry company do not match."))
	if getdate(source.get(mapping.posting_date_field)) != getdate(gl.posting_date):
		frappe.throw(_("Source and GL Entry posting date do not match."))
	return gl, source


def account_default(company, account, posting_date):
	mapping = frappe.qb.DocType("TZ Tax Account Mapping")
	rows = (
		frappe.qb.from_(mapping)
		.select(mapping.tax_category)
		.where((mapping.company == company) & (mapping.account == account) & (mapping.enabled == 1))
		.where(mapping.valid_from <= posting_date)
		.where(mapping.valid_to.isnull() | (mapping.valid_to >= posting_date))
	).run(as_dict=True)
	if len(rows) > 1:
		frappe.throw(_("Overlapping tax account mappings must be resolved first."))
	if rows and not frappe.get_cached_value("TZ Tax Category", rows[0].tax_category, "disabled"):
		return rows[0].tax_category


def evidence_issues(review):
	needed = any(
		frappe.get_cached_value("TZ Tax Category", row.tax_category, "evidence_required")
		for row in review.allocations
	)
	if not needed:
		return []
	usable = [
		row
		for row in review.evidence
		if row.attachment
		and (not row.valid_until or getdate(row.valid_until) >= getdate(review.posting_date))
		and frappe.db.exists("File", {"file_url": row.attachment})
	]
	return [] if usable else [_("Supporting evidence valid at the posting date is required.")]


def validate_review(doc):
	gl, source = source_context(doc.gl_entry)
	previous = doc.get_doc_before_save()
	if previous and previous.gl_entry != doc.gl_entry:
		frappe.throw(_("Create a new review to classify a different GL Entry."))
	if frappe.db.exists(
		"TZ Tax Transaction Review",
		{
			"gl_entry": doc.gl_entry,
			"docstatus": ["!=", 2],
			"name": ["!=", doc.name or ""],
		},
	):
		frappe.throw(_("An active tax review already exists for this GL Entry."))
	doc.active_gl_entry = gl.name
	doc.company = gl.company
	doc.posting_date = gl.posting_date
	doc.source_doctype = gl.voucher_type
	doc.source_name = gl.voucher_no
	doc.source_detail = gl.voucher_detail_no
	doc.account = gl.account
	doc.net_amount = gl.debit - gl.credit
	doc.currency = frappe.get_cached_value("Company", gl.company, "default_currency")
	doc.source_fingerprint = fingerprint(gl.as_dict(), source.modified)
	for row in doc.allocations:
		category = frappe.get_cached_doc("TZ Tax Category", row.tax_category)
		if category.disabled:
			frappe.throw(_("Disabled tax categories cannot be used."))
	try:
		validate_allocations(
			doc.net_amount, [row.amount for row in doc.allocations], doc.precision("net_amount")
		)
	except ValueError as exc:
		frappe.throw(str(exc))
	# Approval fields cannot be supplied by the preparer.
	doc.reviewed_by = None
	doc.reviewed_on = None


def approve_review(doc):
	issues = evidence_issues(doc)
	if issues and not doc.evidence_exception_reason:
		frappe.throw(" ".join(issues))
	for row in doc.allocations:
		if frappe.get_cached_value("TZ Tax Category", row.tax_category, "treatment") == "Review Required":
			frappe.throw(_("Resolve Review Required classifications before submitting."))
	doc.reviewed_by = frappe.session.user
	doc.reviewed_on = now_datetime()


@frappe.whitelist()
def new_review(gl_entry):
	frappe.has_permission("TZ Tax Transaction Review", "create", throw=True)
	gl, _source = source_context(gl_entry)
	existing = frappe.get_list(
		"TZ Tax Transaction Review",
		filters={
			"gl_entry": gl_entry,
			"docstatus": ["!=", 2],
		},
		pluck="name",
		page_length=1,
	)
	if existing:
		return frappe.get_doc("TZ Tax Transaction Review", existing[0]).as_dict()
	doc = frappe.new_doc("TZ Tax Transaction Review")
	doc.gl_entry = gl_entry
	category = account_default(gl.company, gl.account, gl.posting_date)
	if category:
		doc.append(
			"allocations",
			{
				"tax_category": category,
				"amount": gl.debit - gl.credit,
				"reason": _("Default from effective account mapping; confirm before approval."),
			},
		)
	# Populate display fields without saving or requiring allocations yet.
	for key, value in {
		"company": gl.company,
		"posting_date": gl.posting_date,
		"source_doctype": gl.voucher_type,
		"source_name": gl.voucher_no,
		"account": gl.account,
		"source_detail": gl.voucher_detail_no,
		"net_amount": gl.debit - gl.credit,
		"currency": frappe.get_cached_value("Company", gl.company, "default_currency"),
	}.items():
		doc.set(key, value)
	return doc.as_dict()


@frappe.whitelist()
def source_entries(source_doctype, source_name):
	mapping = frappe.get_doc("TZ Tax Source Mapping", source_doctype)
	mapping.check_permission("read")
	if not mapping.enabled:
		return []
	source = frappe.get_doc(source_doctype, source_name)
	source.check_permission("read")
	return frappe.get_list(
		"GL Entry",
		filters={
			"voucher_type": source_doctype,
			"voucher_no": source_name,
			"is_cancelled": 0,
		},
		fields=GL_FIELDS,
		page_length=0,
		order_by="account, name",
	)


def allow_source_cancellation(doc, method=None):
	"""An audit extension must not block the accounting voucher's cancellation."""
	ignored = list(doc.get("ignore_linked_doctypes") or [])
	if "TZ Tax Transaction Review" not in ignored:
		ignored.append("TZ Tax Transaction Review")
	doc.ignore_linked_doctypes = ignored
