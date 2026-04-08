"""Salary Calculator page backend.

Provides a resilient calculation engine that handles salary structures whose
formulas/conditions reference external variables (absent_days, advance, etc.)
by silently setting those components to zero instead of crashing.
"""
from __future__ import annotations

import json
import re

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt


# ── Constants ────────────────────────────────────────────────────────

_SAFE_GLOBALS = {"int": int, "float": float, "round": round, "abs": abs, "min": min, "max": max, "flt": flt}
_BOOLEAN_PREFIXES = ("custom_deduct_", "deduct_", "include_", "custom_")


# ── Public API ───────────────────────────────────────────────────────

@frappe.whitelist()
def get_salary_structure_components(salary_structure):
    """Return earnings/deductions for a salary structure with unique keys."""
    structure = frappe.get_cached_doc("Salary Structure", salary_structure)

    def serialize(rows, prefix):
        return [
            {
                "key": f"{prefix}-{i}",
                "salary_component": row.salary_component,
                "abbr": row.abbr,
                "amount": flt(row.amount),
                "amount_based_on_formula": row.amount_based_on_formula,
                "formula": row.formula or "",
                "condition": row.condition or "",
                "do_not_include_in_total": row.do_not_include_in_total,
                "statistical_component": row.statistical_component,
            }
            for i, row in enumerate(rows)
        ]

    return {
        "earnings": serialize(structure.earnings, "E"),
        "deductions": serialize(structure.deductions, "D"),
        "currency": structure.currency or "",
    }


@frappe.whitelist()
def run_calculation(salary_structure, calculate_based_on, gross_pay=0, net_pay=0, selected_components=None):
    """Run salary calculation with resilient formula evaluation."""
    if isinstance(selected_components, str):
        selected_components = json.loads(selected_components)
    selected = list(dict.fromkeys(selected_components or []))

    structure = frappe.get_cached_doc("Salary Structure", salary_structure)
    precision = 0 if cstr(structure.currency) == "TZS" else 2
    target_field = "gross_pay" if calculate_based_on == "Gross Pay" else "net_pay"
    target_amount = flt({"gross_pay": gross_pay, "net_pay": net_pay}[target_field], precision)

    if target_amount <= 0:
        return _empty_result(precision)

    return _solve(structure, target_field, target_amount, precision, selected)


@frappe.whitelist()
def get_salary_slip_preview(employee, salary_structure, base, gross_pay, net_pay, earnings_data, deductions_data):
    """Render a salary slip preview from calculated data."""
    if isinstance(earnings_data, str):
        earnings_data = json.loads(earnings_data)
    if isinstance(deductions_data, str):
        deductions_data = json.loads(deductions_data)

    emp = frappe.get_cached_doc("Employee", employee)
    currency = frappe.get_cached_value("Salary Structure", salary_structure, "currency") or "TZS"
    fmt = (lambda a: format(flt(a), ",.0f")) if currency == "TZS" else (lambda a: format(flt(a), ",.2f"))

    return frappe.render_template(
        "csf_tz/csf_tz/page/salary_calculator/salary_slip_preview.html",
        {
            "employee": employee,
            "employee_name": emp.employee_name,
            "department": emp.department or "",
            "designation": emp.designation or "",
            "company": emp.company,
            "salary_structure": salary_structure,
            "currency": currency,
            "base": flt(base),
            "gross_pay": flt(gross_pay),
            "net_pay": flt(net_pay),
            "total_earning": sum(flt(e.get("amount")) for e in earnings_data),
            "total_deduction": sum(flt(d.get("amount")) for d in deductions_data),
            "earnings": earnings_data,
            "deductions": deductions_data,
            "format_amount": fmt,
        },
    )


@frappe.whitelist()
def create_salary_structure_assignment(employee, salary_structure, from_date, base=0):
    """Create and submit a Salary Structure Assignment."""
    if frappe.db.exists(
        "Salary Structure Assignment",
        {"employee": employee, "salary_structure": salary_structure, "from_date": from_date, "docstatus": ["!=", 2]},
    ):
        frappe.throw(
            _("Salary Structure Assignment already exists for {0} with {1} from {2}").format(
                frappe.bold(employee), frappe.bold(salary_structure), frappe.bold(from_date),
            )
        )

    ssa = frappe.new_doc("Salary Structure Assignment")
    ssa.employee = employee
    ssa.salary_structure = salary_structure
    ssa.from_date = from_date
    ssa.base = flt(base)
    ssa.company = frappe.get_cached_value("Employee", employee, "company")
    ssa.save()
    ssa.submit()
    return ssa.name


# ── Resilient Calculation Engine ─────────────────────────────────────

def _empty_result(precision=0):
    return {"base": 0, "gross_pay": 0, "net_pay": 0, "total_deductions": 0, "results": []}


def _solve(structure, target_field, target_amount, precision, selected):
    """Binary search for the base amount that produces the target gross/net pay."""
    tol = 1 if precision == 0 else 0.05
    lo, hi = 0.0, max(target_amount, 1)
    best, best_diff = None, None

    # Phase 1: find upper bound
    for i in range(20):
        r = _calc(structure, hi, precision, selected)
        val = flt(r[target_field], precision)
        if val >= target_amount:
            best, best_diff = r, abs(val - target_amount)
            break
        # If doubling base doesn't change the target value, formulas aren't responding
        if i > 2 and val == 0:
            return _empty_result(precision)
        hi *= 2
    else:
        best = r
        best_diff = abs(flt(r[target_field], precision) - target_amount)

    # Phase 2: binary search
    for _ in range(60):
        mid = (lo + hi) / 2
        r = _calc(structure, mid, precision, selected)
        diff = flt(r[target_field], precision) - target_amount
        if abs(diff) < (best_diff or float("inf")):
            best, best_diff = r, abs(diff)
        if abs(diff) <= tol:
            break
        if diff < 0:
            lo = mid
        else:
            hi = mid

    # Phase 3: refine around best integer
    base_int = int(round(flt(best["base"], precision)))
    for offset in range(-3, 4):
        cand = base_int + offset
        if cand < 0:
            continue
        r = _calc(structure, cand, precision, selected)
        d = abs(flt(r[target_field], precision) - target_amount)
        if d < best_diff or (d == best_diff and flt(r[target_field], precision) >= flt(best[target_field], precision)):
            best, best_diff = r, d

    return best


def _calc(structure, base_amount, precision, selected):
    """Calculate salary from a base amount with resilient formula evaluation."""
    rows = _init_rows(structure, precision)
    gross_pay = net_pay = total_ded = 0.0
    prev = None

    for _ in range(10):
        ctx = {"base": flt(base_amount, precision), "gross_pay": gross_pay, "net_pay": net_pay, "total_deductions": total_ded}
        _add_row_ctx(ctx, rows["earnings"] + rows["deductions"], precision)
        _add_flag_ctx(ctx, rows["earnings"] + rows["deductions"], selected)

        earnings = _eval_rows(rows["earnings"], ctx, precision, selected)
        gross_pay = flt(sum(r.amount for r in earnings if _incl_gross(r, selected)), precision)
        ctx.update({"gross_pay": gross_pay})
        _add_row_ctx(ctx, earnings, precision)

        deductions = _eval_rows(rows["deductions"], ctx, precision, selected)
        total_ded = flt(sum(r.amount for r in deductions if _incl_ded(r, selected)), precision)
        net_pay = flt(gross_pay - total_ded, precision)

        state = (gross_pay, total_ded, net_pay, tuple(r.amount for r in earnings + deductions))
        rows = {"earnings": earnings, "deductions": deductions}
        if state == prev:
            break
        prev = state

    all_rows = earnings + deductions
    results = _build_results(selected, all_rows, precision)
    return {
        "base": flt(base_amount, precision),
        "gross_pay": gross_pay,
        "net_pay": net_pay,
        "total_deductions": total_ded,
        "results": results,
    }


def _init_rows(structure, precision):
    def norm(row, ctype):
        return frappe._dict(
            salary_component=cstr(row.salary_component), abbr=cstr(row.abbr), component_type=ctype,
            condition=cstr(row.condition), formula=cstr(row.formula),
            amount=flt(row.amount, precision), amount_based_on_formula=cint(row.amount_based_on_formula),
            do_not_include_in_total=cint(row.do_not_include_in_total), statistical_component=cint(row.statistical_component),
        )
    return {
        "earnings": [norm(r, "Earning") for r in structure.earnings],
        "deductions": [norm(r, "Deduction") for r in structure.deductions],
    }


def _add_row_ctx(ctx, rows, precision):
    for r in rows:
        if r.abbr:
            ctx[r.abbr] = flt(r.amount, precision)
            ctx[f"{r.abbr}_amount"] = flt(r.amount, precision)


def _add_flag_ctx(ctx, rows, selected):
    """Infer boolean/numeric flags from formulas and conditions."""
    exprs = [r.condition for r in rows if r.condition] + [r.formula for r in rows if r.formula]
    tokens = {
        tok for expr in exprs
        for tok in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", expr)
        if any(tok.startswith(p) for p in _BOOLEAN_PREFIXES)
    }
    for tok in tokens:
        if tok.startswith(_BOOLEAN_PREFIXES):
            kw = tok
            for p in _BOOLEAN_PREFIXES:
                if kw.startswith(p):
                    kw = kw[len(p):]
                    break
            norm = kw.replace("_", "").lower()
            sel_text = " ".join(selected).replace(" ", "").replace("_", "").lower()
            ctx.setdefault(tok, 1 if norm and norm in sel_text else 0)
        else:
            ctx.setdefault(tok, 0)


def _eval_rows(rows, base_ctx, precision, selected):
    ctx = frappe._dict(base_ctx.copy())
    result = []
    for row in rows:
        amt = row.amount if not row.amount_based_on_formula else 0
        if not _should_eval(row, selected):
            amt = 0
        elif row.condition and not _safe_condition(row.condition, ctx):
            amt = 0
        elif row.amount_based_on_formula and row.formula:
            amt = _safe_formula(row.formula, ctx, precision)

        row.amount = flt(amt, precision)
        result.append(row)
        if row.abbr:
            ctx[row.abbr] = row.amount
            ctx[f"{row.abbr}_amount"] = row.amount
    return result


def _safe_formula(formula, ctx, precision):
    """Evaluate a formula, returning 0 on any error."""
    try:
        return flt(frappe.safe_eval(cstr(formula).strip(), eval_globals=_SAFE_GLOBALS, eval_locals=ctx), precision)
    except Exception:
        return 0


def _safe_condition(condition, ctx):
    """Evaluate a condition, returning False on any error."""
    try:
        return cint(frappe.safe_eval(cstr(condition).strip(), eval_globals=_SAFE_GLOBALS, eval_locals=ctx))
    except Exception:
        return False


def _is_base(row):
    f = cstr(row.formula).replace(" ", "").lower()
    return row.abbr == "B" or cstr(row.salary_component).lower() == "basic" or f == "base"


def _should_eval(row, selected):
    if row.statistical_component or _is_base(row):
        return True
    return cstr(row.salary_component) in set(selected)


def _incl_gross(row, selected):
    if row.component_type != "Earning" or row.do_not_include_in_total or row.statistical_component:
        return False
    return _is_base(row) or cstr(row.salary_component) in set(selected)


def _incl_ded(row, selected):
    if row.component_type != "Deduction" or row.do_not_include_in_total or row.statistical_component:
        return False
    return cstr(row.salary_component) in set(selected)


def _build_results(selected, all_rows, precision):
    amounts = {}
    for r in all_rows:
        name = cstr(r.salary_component)
        if name:
            amounts[name] = flt(amounts.get(name, 0) + flt(r.amount, precision), precision)
    return [{"salary_component": c, "amount": flt(amounts.get(c, 0), precision)} for c in selected]
