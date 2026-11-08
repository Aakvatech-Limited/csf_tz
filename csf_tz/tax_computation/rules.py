"""Pure Phase 1 review helpers; no tax rates or annual tax computation."""

import hashlib
import json
from decimal import Decimal, InvalidOperation


def fingerprint(gl, source_modified):
	keys = (
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
	)
	payload = {key: str(gl.get(key) or "") for key in keys}
	payload["source_modified"] = str(source_modified)
	return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def validate_allocations(net_amount, amounts, precision=2):
	"""Signed company-currency allocations must exhaust exactly one GL posting."""
	quantum = Decimal(1).scaleb(-precision)
	try:
		net = Decimal(str(net_amount)).quantize(quantum)
		parts = [Decimal(str(value)).quantize(quantum) for value in amounts]
		if not net.is_finite() or any(not part.is_finite() for part in parts):
			raise ValueError("Amounts must be finite")
		if not parts or any(part == 0 or (part > 0) != (net > 0) for part in parts):
			raise ValueError("Allocations must be non-zero and have the same sign as the GL net amount")
		if sum(parts) != net:
			raise ValueError("Allocation amounts must equal the GL net amount in company currency")
	except InvalidOperation as exc:
		raise ValueError("Invalid allocation amount") from exc


def review_status(review, current_fingerprint, evidence_issues):
	if not review:
		return "Unreviewed"
	if review.source_fingerprint != current_fingerprint:
		return "Source Changed"
	if review.docstatus != 1:
		return "Draft Review"
	if evidence_issues:
		return "Reviewed with Exception" if review.evidence_exception_reason else "Evidence Required"
	return "Reviewed"


def resolve_default(mappings, posting_date):
	date = str(posting_date)
	matches = [
		row["tax_category"]
		for row in mappings
		if str(row["valid_from"]) <= date and (not row.get("valid_to") or str(row["valid_to"]) >= date)
	]
	if len(matches) > 1:
		raise ValueError("Overlapping tax account mappings must be resolved first")
	return matches[0] if matches else None
