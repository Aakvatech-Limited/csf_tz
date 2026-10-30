"""Idempotent provider registration. Credentials remain company-specific."""
import frappe


def ensure_pergamon_provider():
    if not frappe.db.exists("DocType", "Pergamon VFD Settings"):
        return
    existing = frappe.db.get_value(
        "VFD Provider", {"vfd_provider_settings": "Pergamon VFD Settings"}, "name"
    )
    if existing:
        return
    provider = frappe.get_doc({
        "doctype": "VFD Provider",
        "vfd_provider": "Pergamon",
        "vfd_provider_settings": "Pergamon VFD Settings",
        "sandbox": 0,
    })
    provider.insert(ignore_permissions=True)
