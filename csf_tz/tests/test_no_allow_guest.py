# Tests that user-facing @frappe.whitelist() endpoints do not allow guest access.
# A guest call must be refused with PermissionError (HTTP 403).
# The only endpoints that may carry allow_guest=True are real external callbacks
# in bank_api.py (receive_callback, receive_validate_reference).
import ast
import unittest
from pathlib import Path


def _get_whitelisted_functions(filepath):
    """Return list of (function_name, allow_guest) tuples for @frappe.whitelist decorated functions."""
    source = Path(filepath).read_text()
    tree = ast.parse(source)
    results = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            # Match @frappe.whitelist(...) or @frappe.whitelist
            if isinstance(decorator, ast.Attribute):
                # bare @frappe.whitelist
                if decorator.attr == "whitelist":
                    results.append((node.name, False))
            elif isinstance(decorator, ast.Call):
                func = decorator.func
                if isinstance(func, ast.Attribute) and func.attr == "whitelist":
                    allow_guest = False
                    for kw in decorator.keywords:
                        if kw.arg == "allow_guest" and isinstance(
                            kw.value, ast.Constant
                        ):
                            allow_guest = bool(kw.value.value)
                    results.append((node.name, allow_guest))
    return results


APP_ROOT = Path(__file__).parents[2]  # csf_tz/csf_tz/

# Files that must have NO allow_guest=True
USER_FACING_FILES = [
    "after_sales_services/doctype/requested_payments/requested_payments.py",
    "workshop/doctype/requested_items/requested_items.py",
    "fleet_management/doctype/fuel_request/fuel_request.py",
    "fleet_management/doctype/transport_request/transport_request.py",
    "fleet_management/doctype/vehicle_trip/vehicle_trip.py",
    "fleet_management/doctype/transport_assignment/transport_assignment.py",
    "clearing_and_forwarding/doctype/bond/bond.py",
    "clearing_and_forwarding/doctype/border_clearance/border_clearance.py",
    "clearing_and_forwarding/doctype/container_issue/container_issue.py",
    "clearing_and_forwarding/doctype/container/container.py",
    "clearing_and_forwarding/doctype/container_entry/container_entry.py",
    "clearing_and_forwarding/doctype/export/export.py",
    "clearing_and_forwarding/doctype/files/files.py",
    "clearing_and_forwarding/doctype/border_processing/border_processing.py",
    "clearing_and_forwarding/doctype/import/import.py",
    "csf_tz/doctype/tra_tax_inv/tra_tax_inv.py",
]

# Real external bank callbacks that legitimately keep allow_guest=True
ALLOWED_GUEST_ENDPOINTS = {
    "bank_api.py": {"receive_callback", "receive_validate_reference"},
}


class TestNoAllowGuest(unittest.TestCase):
    def test_user_facing_files_have_no_allow_guest(self):
        violations = []
        for rel_path in USER_FACING_FILES:
            full_path = APP_ROOT / rel_path
            if not full_path.exists():
                continue
            for fn_name, allow_guest in _get_whitelisted_functions(full_path):
                if allow_guest:
                    violations.append(f"{rel_path}:{fn_name}")
        self.assertEqual(
            violations,
            [],
            "These endpoints must not use allow_guest=True:\n" + "\n".join(violations),
        )

    def test_bank_api_keeps_allow_guest_for_callbacks(self):
        bank_api = APP_ROOT / "csf_tz/bank_api.py"
        if not bank_api.exists():
            self.skipTest("bank_api.py not found")
        guest_fns = {fn for fn, ag in _get_whitelisted_functions(bank_api) if ag}
        required = ALLOWED_GUEST_ENDPOINTS["bank_api.py"]
        self.assertTrue(
            required.issubset(guest_fns),
            f"Expected {required} to still have allow_guest=True, found: {guest_fns}",
        )
