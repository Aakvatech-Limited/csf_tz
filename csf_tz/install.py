import frappe
from frappe import _


def before_migrate():
    """Require the new owner before retiring shared module definitions."""
    if "av_tools" not in frappe.get_installed_apps():
        frappe.throw(
            _(
                "Install av_tools before migrating csf_tz; it now owns "
                "AuthOTP, Feedback, AI Integration and Trade In."
            )
        )

    # Keep this self-contained so existing sites can update the two apps in either
    # order. Installing AV Tools first still needs its normal before_install hook.
    for module in ("AuthOTP", "Feedback", "AI Integration", "Trade In"):
        if frappe.db.get_value("Module Def", module, "app_name") == "csf_tz":
            frappe.db.set_value(
                "Module Def", module, "app_name", "av_tools", update_modified=False
            )

    if frappe.db.get_value("DocType", "OTP Register", "module") == "CSF TZ":
        frappe.db.set_value(
            "DocType", "OTP Register", "module", "AuthOTP", update_modified=False
        )
        frappe.clear_cache(doctype="OTP Register")
