from frappe.database.query import RawCriterion
from frappe.desk.reportview import build_match_conditions


def get_match_criterion(doctype):
	"""User permission conditions of `doctype` as a bracketed criterion, or None for an unrestricted user.

	`build_match_conditions` escapes `%` in permission query conditions, which qb runs as a format string.
	"""
	if conditions := build_match_conditions(doctype):
		return RawCriterion(f"({conditions})")
