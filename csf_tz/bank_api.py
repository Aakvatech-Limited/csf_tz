"""Deprecated. The NMB fee integration moved to the edu_tz app.

Only `receive_callback` remains, because NMB stores that URL against invoices
submitted before the move. Everything else moved to edu_tz.edu_tz.nmb.api.
"""

import frappe
from frappe import _


# nosemgrep: guest-whitelisted-method -- NMB posts payment callbacks unauthenticated
@frappe.whitelist(allow_guest=True)
def receive_callback(*args, **kwargs):
    """Forwards legacy NMB callbacks to edu_tz."""
    if "edu_tz" not in frappe.get_installed_apps():
        frappe.throw(_("The NMB fee integration has moved to the edu_tz app."))

    from edu_tz.edu_tz.nmb.api import receive_callback as handler

    return handler(*args, **kwargs)
