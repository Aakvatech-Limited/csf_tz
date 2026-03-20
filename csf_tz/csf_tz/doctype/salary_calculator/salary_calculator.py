# Copyright (c) 2026, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr, flt


DEFAULT_AMOUNT_PRECISION = 2
SAFE_EVAL_GLOBALS = {
	"int": int,
	"float": float,
	"round": round,
	"abs": abs,
	"min": min,
	"max": max,
	"flt": flt,
}
BOOLEAN_PREFIXES = ("custom_deduct_", "deduct_", "include_")
NUMERIC_PREFIX = "custom_"


class SalaryCalculator(Document):
	def validate(self):
		self.run_calculation()

	def run_calculation(self):
		result = calculate_salary(doc=self.as_dict())
		apply_result(self, result)


@frappe.whitelist()
def calculate_salary(doc=None, **kwargs):
	data = get_input_data(doc, kwargs)

	if not data.salary_structure or not data.calculate_based_on:
		return empty_result()

	structure = frappe.get_cached_doc("Salary Structure", data.salary_structure)
	precision = get_amount_precision(structure)
	selected_components = get_selected_components(data)
	validate_selected_components(structure, selected_components)
	target_field = "gross_pay" if data.calculate_based_on == "Gross Pay" else "net_pay"
	target_amount = flt(data.get(target_field), precision)
	if target_amount <= 0:
		return empty_result(precision)

	result = solve_base_for_target(
		structure,
		data.calculate_based_on,
		target_amount,
		precision,
		selected_components,
		data.allowance,
	)
	result["salary_structure"] = structure.name
	return result


def get_input_data(doc, kwargs):
	if isinstance(doc, str):
		doc = json.loads(doc)

	data = frappe._dict(doc or {})
	data.update(kwargs)

	data.salary_structure = cstr(data.get("salary_structure"))
	data.calculate_based_on = cstr(data.get("calculate_based_on"))
	data.gross_pay = flt(data.get("gross_pay"))
	data.net_pay = flt(data.get("net_pay"))
	data.allowance = flt(data.get("allowance"))
	data.results = [frappe._dict(row) for row in (data.get("results") or [])]

	return data


def empty_result(precision=DEFAULT_AMOUNT_PRECISION):
	return {
		"base": 0,
		"gross_pay": 0,
		"net_pay": 0,
		"total_deductions": 0,
		"results": [],
		"calculation_summary": build_summary_html(0, 0, 0, [], precision=precision),
	}


def apply_result(doc, result):
	doc.base = result["base"]
	doc.gross_pay = result["gross_pay"]
	doc.net_pay = result["net_pay"]
	doc.total_deductions = result["total_deductions"]
	doc.calculation_summary = result["calculation_summary"]

	doc.set("results", [])
	for row in result["results"]:
		doc.append(
			"results",
			{
				"salary_component": row["salary_component"],
				"amount": row["amount"],
			},
		)


def solve_base_for_target(structure, calculate_based_on, target_amount, precision, selected_components, allowance=0):
	target_field = "gross_pay" if calculate_based_on == "Gross Pay" else "net_pay"
	lower_bound = 0.0
	upper_bound = max(target_amount, 1)
	best_result = None
	best_difference = None

	for _ in range(20):
		result = calculate_from_base(structure, upper_bound, precision, selected_components, allowance)
		current_value = flt(result[target_field], precision)
		if current_value >= target_amount:
			best_result = result
			best_difference = abs(current_value - target_amount)
			break
		upper_bound *= 2
	else:
		best_result = result
		best_difference = abs(flt(result[target_field], precision) - target_amount)

	for _ in range(60):
		candidate_base = (lower_bound + upper_bound) / 2
		result = calculate_from_base(structure, candidate_base, precision, selected_components, allowance)
		difference = flt(result[target_field], precision) - target_amount

		if best_difference is None or abs(difference) < best_difference:
			best_difference = abs(difference)
			best_result = result

		if abs(difference) <= get_tolerance(precision):
			best_result = result
			break

		if difference < 0:
			lower_bound = candidate_base
		else:
			upper_bound = candidate_base

	return refine_best_result(
		structure,
		best_result,
		target_field,
			target_amount,
			precision,
			selected_components,
			allowance,
		)


def calculate_from_base(structure, base_amount, precision, selected_components, allowance=0):
	gross_pay = 0.0
	net_pay = 0.0
	total_deductions = 0.0
	allowance = flt(allowance, precision)
	evaluated_rows = initialize_rows(structure, precision)
	previous_state = None

	for _ in range(10):
		context = get_initial_context(
			base_amount,
			gross_pay,
			net_pay,
			total_deductions,
			evaluated_rows,
			precision,
			selected_components,
			allowance,
		)
		earnings = evaluate_rows(evaluated_rows["earnings"], context, precision, selected_components)
		earnings_total = flt(
			sum(
				row.amount
				for row in earnings
				if should_include_in_gross(row, selected_components)
			),
			precision,
		)
		gross_pay = flt(earnings_total + allowance, precision)

		context.update(get_row_context(earnings, precision))
		context["gross_pay"] = gross_pay

		deductions = evaluate_rows(evaluated_rows["deductions"], context, precision, selected_components)
		total_deductions = flt(
			sum(
				row.amount
				for row in deductions
				if should_include_in_total_deductions(row, selected_components)
			),
			precision,
		)
		net_pay = flt(gross_pay - total_deductions, precision)

		current_state = (
			gross_pay,
			total_deductions,
			net_pay,
			tuple(row.amount for row in earnings + deductions),
		)

		evaluated_rows = {"earnings": earnings, "deductions": deductions}
		if current_state == previous_state:
			break
		previous_state = current_state

	all_rows = earnings + deductions
	selected_results = build_selected_results(selected_components, all_rows, precision)
	return {
		"base": flt(base_amount, precision),
		"allowance": allowance,
		"gross_pay": gross_pay,
		"net_pay": net_pay,
		"total_deductions": total_deductions,
		"results": selected_results,
		"calculation_summary": build_summary_html(
			flt(base_amount, precision),
			gross_pay,
			net_pay,
			[(row["salary_component"], row["amount"]) for row in selected_results],
			total_deductions=total_deductions,
			precision=precision,
			allowance=allowance,
		),
	}


def initialize_rows(structure, precision):
	return {
		"earnings": [normalize_row(row, "Earning", precision) for row in structure.earnings],
		"deductions": [normalize_row(row, "Deduction", precision) for row in structure.deductions],
	}


def normalize_row(row, component_type, precision):
	return frappe._dict(
		salary_component=cstr(row.salary_component),
		abbr=cstr(row.abbr),
		component_type=component_type,
		condition=cstr(row.condition),
		formula=cstr(row.formula),
		amount=flt(row.amount, precision),
		amount_based_on_formula=cint(row.amount_based_on_formula),
		do_not_include_in_total=cint(row.do_not_include_in_total),
		statistical_component=cint(row.statistical_component),
	)


def get_initial_context(
	base_amount, gross_pay, net_pay, total_deductions, evaluated_rows, precision, selected_components, allowance=0
):
	context = {
		"base": flt(base_amount, precision),
		"allowance": flt(allowance, precision),
		"gross_pay": flt(gross_pay, precision),
		"net_pay": flt(net_pay, precision),
		"total_deductions": flt(total_deductions, precision),
	}
	context.update(get_row_context(evaluated_rows["earnings"] + evaluated_rows["deductions"], precision))
	context.update(get_custom_context(evaluated_rows["earnings"] + evaluated_rows["deductions"], selected_components))
	return context


def get_row_context(rows, precision):
	context = {}
	for row in rows:
		if row.abbr:
			context[row.abbr] = flt(row.amount, precision)
			context[f"{row.abbr}_amount"] = flt(row.amount, precision)
	return context


def get_custom_context(rows, selected_components):
	expressions = []
	for row in rows:
		if row.condition:
			expressions.append(row.condition)
		if row.formula:
			expressions.append(row.formula)

	tokens = {
		token
		for expression in expressions
		for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", expression)
		if token.startswith(NUMERIC_PREFIX) or token.startswith(BOOLEAN_PREFIXES)
	}

	context = {}
	for token in tokens:
		if token.startswith(BOOLEAN_PREFIXES):
			context[token] = infer_boolean_flag(token, selected_components)
		elif token not in context:
			context[token] = 0
	return context


def evaluate_rows(rows, base_context, precision, selected_components):
	context = frappe._dict(base_context.copy())
	evaluated = []

	for row in rows:
		amount = row.amount if not row.amount_based_on_formula else 0
		if not should_evaluate_row(row, selected_components):
			amount = 0
		elif row.condition and not evaluate_condition(row.condition, context, row.salary_component):
			amount = 0
		elif row.amount_based_on_formula and row.formula:
			amount = evaluate_formula(row.formula, context, row.salary_component, precision)

		row.amount = flt(amount, precision)
		evaluated.append(row)

		if row.abbr:
			context[row.abbr] = row.amount
			context[f"{row.abbr}_amount"] = row.amount

	return evaluated


def evaluate_formula(formula, context, label, precision):
	try:
		return flt(
			frappe.safe_eval(
				cstr(formula).strip(),
				eval_globals=SAFE_EVAL_GLOBALS,
				eval_locals=context,
			),
			precision,
		)
	except Exception as exc:
		frappe.throw(_("{0} formula error: {1}").format(label, exc))


def evaluate_condition(condition, context, label):
	try:
		return cint(
			frappe.safe_eval(
				cstr(condition).strip(),
				eval_globals=SAFE_EVAL_GLOBALS,
				eval_locals=context,
			)
		)
	except Exception as exc:
		frappe.throw(_("{0} condition error: {1}").format(label, exc))


def build_summary_html(
	base, gross_pay, net_pay, component_rows, total_deductions=0, precision=DEFAULT_AMOUNT_PRECISION, allowance=0
):
	rows = [("Base", base)]
	if flt(allowance, precision):
		rows.append(("Allowance", allowance))
	rows.extend(component_rows)
	rows.extend(
		[
			("Total Deductions", total_deductions),
			("Gross Pay", gross_pay),
			("Net Pay", net_pay),
		]
	)

	table_rows = "".join(
		f"<tr><td><strong>{label}</strong></td><td style='text-align:right'>{format_amount(amount, precision)}</td></tr>"
		for label, amount in rows
	)

	return (
		"<div style='padding: 10px;'>"
		"<h4><strong>Calculated Values</strong></h4>"
		"<table class='table table-bordered'>"
		f"{table_rows}"
		"</table>"
		"</div>"
	)


def format_amount(amount, precision=DEFAULT_AMOUNT_PRECISION):
	format_spec = f",.{precision}f"
	return format(flt(amount, precision), format_spec)


def get_amount_precision(structure):
	if cstr(getattr(structure, "currency", "")) == "TZS":
		return 0
	return DEFAULT_AMOUNT_PRECISION


def get_tolerance(precision):
	return 1 if precision == 0 else 0.05


def refine_best_result(structure, best_result, target_field, target_amount, precision, selected_components, allowance=0):
	if not best_result:
		return best_result

	base_value = int(round(flt(best_result.get("base"), precision)))
	candidate_bases = {base_value}

	for offset in range(1, 4):
		candidate_bases.add(base_value - offset)
		candidate_bases.add(base_value + offset)

	refined_result = best_result
	refined_difference = abs(flt(best_result.get(target_field), precision) - target_amount)

	for candidate_base in sorted(base for base in candidate_bases if base >= 0):
		result = calculate_from_base(structure, candidate_base, precision, selected_components, allowance)
		difference = abs(flt(result.get(target_field), precision) - target_amount)

		if difference < refined_difference:
			refined_result = result
			refined_difference = difference
		elif difference == refined_difference and flt(result.get(target_field), precision) >= flt(
			refined_result.get(target_field), precision
		):
			refined_result = result

	return refined_result


def get_selected_components(data):
	return [cstr(row.get("salary_component")) for row in (data.get("results") or []) if cstr(row.get("salary_component"))]


def validate_selected_components(structure, selected_components):
	if not selected_components:
		return

	duplicates = sorted({component for component in selected_components if selected_components.count(component) > 1})
	if duplicates:
		frappe.throw(_("Duplicate salary components are not allowed: {0}").format(", ".join(duplicates)))

	available_components = {
		cstr(row.salary_component) for row in list(structure.earnings) + list(structure.deductions) if cstr(row.salary_component)
	}
	missing_components = [component for component in selected_components if component not in available_components]
	if missing_components:
		frappe.throw(
			_("These salary components are not in salary structure {0}: {1}").format(
				frappe.bold(structure.name), ", ".join(missing_components)
			)
		)


def should_evaluate_row(row, selected_components):
	if row.statistical_component:
		return True

	if is_base_row(row):
		return True

	return is_selected_component(row.salary_component, selected_components)


def should_include_in_gross(row, selected_components):
	if row.component_type != "Earning" or row.do_not_include_in_total or row.statistical_component:
		return False

	return is_base_row(row) or is_selected_component(row.salary_component, selected_components)


def should_include_in_total_deductions(row, selected_components):
	if row.component_type != "Deduction" or row.do_not_include_in_total or row.statistical_component:
		return False

	return is_selected_component(row.salary_component, selected_components)


def is_base_row(row):
	formula = cstr(row.formula).replace(" ", "").lower()
	return row.abbr == "B" or cstr(row.salary_component).lower() == "basic" or formula == "base"


def is_selected_component(component_name, selected_components):
	return cstr(component_name) in set(selected_components)


def infer_boolean_flag(token, selected_components):
	keyword = token
	for prefix in BOOLEAN_PREFIXES:
		if keyword.startswith(prefix):
			keyword = keyword[len(prefix) :]
			break

	normalized_keyword = keyword.replace("_", "").lower()
	selected_text = " ".join(selected_components).replace(" ", "").replace("_", "").lower()
	return 1 if normalized_keyword and normalized_keyword in selected_text else 0


def build_selected_results(selected_components, all_rows, precision):
	amounts = {}
	for row in all_rows:
		if not cstr(row.salary_component):
			continue
		amounts.setdefault(cstr(row.salary_component), 0)
		amounts[cstr(row.salary_component)] = flt(amounts[cstr(row.salary_component)] + flt(row.amount, precision), precision)

	return [
		{
			"salary_component": component,
			"amount": flt(amounts.get(component, 0), precision),
		}
		for component in selected_components
	]
