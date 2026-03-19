# Copyright (c) 2026, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import annotations

import re
from copy import deepcopy

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate
from hrms.payroll.doctype.salary_structure.salary_structure import make_salary_slip


STATUTORY_COMPONENTS = {
	"nssf": "NSSF",
	"wcf": "WCF",
	"sdl": "SDL",
}
FORMULA_FLAG_PREFIXES = ("custom_", "deduct_", "include_")
AMOUNT_PRECISION = 2


class SalaryCalculator(Document):
	def validate(self):
		self.company = self.company or frappe.db.get_value("Employee", self.employee, "company")
		self.run_calculation()

	def run_calculation(self):
		if not self.employee or not self.calculate_based_on:
			self.reset_results()
			return

		target_amount = flt(self.net_pay if self.calculate_based_on == "Net Pay" else self.gross_pay)
		if target_amount <= 0:
			self.reset_results()
			return

		assignment = get_salary_structure_assignment(self.employee, self.company, nowdate())
		self.company = assignment.company
		self.salary_structure = assignment.salary_structure

		base, slip = solve_base_for_target(
			assignment=assignment,
			target_field="net_pay" if self.calculate_based_on == "Net Pay" else "gross_pay",
			target_amount=target_amount,
			include_map=self.get_component_toggle_map(),
		)

		self.base = base
		self.net_pay = flt(slip.net_pay, AMOUNT_PRECISION)
		self.gross_pay = flt(slip.gross_pay, AMOUNT_PRECISION)
		self.nssf_amount = get_component_amount(slip, STATUTORY_COMPONENTS["nssf"], enabled=self.nssf)
		self.wcf_amount = get_component_amount(slip, STATUTORY_COMPONENTS["wcf"], enabled=self.wcf)
		self.sdl_amount = get_component_amount(slip, STATUTORY_COMPONENTS["sdl"], enabled=self.sdl)

	def get_component_toggle_map(self) -> dict[str, bool]:
		return {key: bool(getattr(self, key)) for key in STATUTORY_COMPONENTS}

	def reset_results(self):
		self.base = 0
		self.salary_structure = None
		self.nssf_amount = 0
		self.wcf_amount = 0
		self.sdl_amount = 0


@frappe.whitelist()
def calculate_salary(
	employee: str,
	company: str | None = None,
	calculate_based_on: str | None = None,
	net_pay: float | None = None,
	gross_pay: float | None = None,
	nssf: int = 0,
	wcf: int = 0,
	sdl: int = 0,
):
	if not employee or not calculate_based_on:
		return {}

	doc = frappe._dict(
		employee=employee,
		company=company,
		calculate_based_on=calculate_based_on,
		net_pay=flt(net_pay),
		gross_pay=flt(gross_pay),
		nssf=nssf,
		wcf=wcf,
		sdl=sdl,
	)

	assignment = get_salary_structure_assignment(doc.employee, doc.company, nowdate())
	target_field = "net_pay" if doc.calculate_based_on == "Net Pay" else "gross_pay"
	target_amount = flt(doc.get(target_field))

	if target_amount <= 0:
		return {
			"company": assignment.company,
			"salary_structure": assignment.salary_structure,
			"base": 0,
			"net_pay": 0,
			"gross_pay": 0,
			"nssf_amount": 0,
			"wcf_amount": 0,
			"sdl_amount": 0,
		}

	base, slip = solve_base_for_target(
		assignment=assignment,
		target_field=target_field,
		target_amount=target_amount,
		include_map={
			"nssf": bool(nssf),
			"wcf": bool(wcf),
			"sdl": bool(sdl),
		},
	)

	return {
		"company": assignment.company,
		"salary_structure": assignment.salary_structure,
		"base": flt(base, AMOUNT_PRECISION),
		"net_pay": flt(slip.net_pay, AMOUNT_PRECISION),
		"gross_pay": flt(slip.gross_pay, AMOUNT_PRECISION),
		"nssf_amount": get_component_amount(slip, STATUTORY_COMPONENTS["nssf"], enabled=nssf),
		"wcf_amount": get_component_amount(slip, STATUTORY_COMPONENTS["wcf"], enabled=wcf),
		"sdl_amount": get_component_amount(slip, STATUTORY_COMPONENTS["sdl"], enabled=sdl),
	}


def get_salary_structure_assignment(employee: str, company: str | None, on_date: str):
	filters = {
		"employee": employee,
		"from_date": ("<=", on_date),
		"docstatus": 1,
	}
	if company:
		filters["company"] = company

	assignment = frappe.db.get_value(
		"Salary Structure Assignment",
		filters,
		[
			"name",
			"employee",
			"salary_structure",
			"company",
			"currency",
			"base",
			"variable",
			"income_tax_slab",
		],
		as_dict=True,
		order_by="from_date desc, modified desc",
	)

	if not assignment:
		frappe.throw(
			_("No submitted Salary Structure Assignment found for employee {0}.").format(
				frappe.bold(employee)
			)
		)

	return assignment


def solve_base_for_target(
	assignment: frappe._dict,
	target_field: str,
	target_amount: float,
	include_map: dict[str, bool],
):
	lower_bound = 0.0
	upper_bound = max(flt(assignment.base) * 2, target_amount * 2, 1)
	tolerance = 0.5
	best_base = 0.0
	best_slip = None
	best_difference = None

	for _ in range(20):
		slip = generate_preview_slip(assignment, upper_bound, include_map)
		current_amount = flt(getattr(slip, target_field))
		if current_amount >= target_amount:
			best_base = upper_bound
			best_slip = slip
			best_difference = abs(current_amount - target_amount)
			break
		upper_bound *= 2
	else:
		best_slip = generate_preview_slip(assignment, upper_bound, include_map)
		best_base = upper_bound
		best_difference = abs(flt(getattr(best_slip, target_field)) - target_amount)

	for _ in range(30):
		candidate_base = (lower_bound + upper_bound) / 2
		slip = generate_preview_slip(assignment, candidate_base, include_map)
		current_amount = flt(getattr(slip, target_field))
		difference = current_amount - target_amount

		if best_difference is None or abs(difference) < best_difference:
			best_difference = abs(difference)
			best_base = candidate_base
			best_slip = slip

		if abs(difference) <= tolerance:
			best_base = candidate_base
			best_slip = slip
			break

		if difference < 0:
			lower_bound = candidate_base
		else:
			upper_bound = candidate_base

	return flt(best_base, AMOUNT_PRECISION), best_slip


def generate_preview_slip(
	assignment: frappe._dict,
	base_amount: float,
	include_map: dict[str, bool],
):
	slip = make_salary_slip(
		assignment.salary_structure,
		employee=assignment.employee,
		posting_date=nowdate(),
		for_preview=1,
		ignore_permissions=True,
	)
	slip.company = assignment.company
	slip._salary_structure_assignment = frappe._dict(deepcopy(dict(assignment)))
	slip._salary_structure_assignment.base = flt(base_amount)
	set_formula_toggle_flags(slip, include_map)

	for component_type in ("earnings", "deductions"):
		for row in slip.get(component_type) or []:
			row.amount = 0
			row.default_amount = 0

	slip.calculate_net_pay()
	apply_component_toggles(slip, include_map)

	return slip


def apply_component_toggles(slip, include_map: dict[str, bool]):
	adjusted = False

	for component_type in ("earnings", "deductions"):
		for row in slip.get(component_type) or []:
			component_key = get_matching_component_key(row.salary_component, row.abbr)
			if component_key and not include_map.get(component_key):
				row.amount = 0
				row.default_amount = 0
				adjusted = True

	if adjusted:
		slip.set_totals()


def set_formula_toggle_flags(slip, include_map: dict[str, bool]):
	if not getattr(slip, "_salary_structure_doc", None):
		slip.set_salary_structure_doc()

	for key, enabled in include_map.items():
		flag = 1 if enabled else 0
		setattr(slip, key, flag)
		setattr(slip, f"deduct_{key}", flag)
		setattr(slip, f"include_{key}", flag)
		slip._salary_structure_assignment[key] = flag
		slip._salary_structure_assignment[f"deduct_{key}"] = flag
		slip._salary_structure_assignment[f"include_{key}"] = flag

	for component_type in ("earnings", "deductions"):
		for row in slip._salary_structure_doc.get(component_type) or []:
			for token in extract_formula_flags(row.condition) | extract_formula_flags(row.formula):
				if token not in slip._salary_structure_assignment:
					setattr(slip, token, 0)
					slip._salary_structure_assignment[token] = 0


def get_component_amount(slip, component_name: str, enabled: bool = True) -> float:
	if not enabled:
		return 0

	total_amount = sum_matching_component_amounts(slip.get("deductions") or [], component_name)
	if total_amount:
		return flt(total_amount, AMOUNT_PRECISION)

	total_amount = sum_matching_component_amounts(slip.get("earnings") or [], component_name)

	return flt(total_amount, AMOUNT_PRECISION)


def get_matching_component_key(*values: str | None) -> str | None:
	for key, label in STATUTORY_COMPONENTS.items():
		if any(is_component_match(value, label) for value in values if value):
			return key

	return None


def normalize_component(value: str | None) -> str:
	return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def is_component_match(value: str | None, component_name: str) -> bool:
	return normalize_component(component_name) in normalize_component(value)


def sum_matching_component_amounts(rows, component_name: str) -> float:
	return sum(
		flt(row.amount, AMOUNT_PRECISION)
		for row in rows
		if is_component_match(row.salary_component, component_name)
	)


def extract_formula_flags(expression: str | None) -> set[str]:
	if not expression:
		return set()

	return {
		token
		for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", expression)
		if token.startswith(FORMULA_FLAG_PREFIXES)
	}

