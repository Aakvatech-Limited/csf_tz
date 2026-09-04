"""Upgrade guards for sites that carried vfd_providers before csf_tz absorbed it."""

import frappe
from frappe import _

RETIRED_APP = "vfd_providers"


def block_stale_vfd_providers():
	"""Refuse to migrate while an old vfd_providers still registers its own VFD handlers.

	csf_tz now owns the handlers. A vfd_providers older than 16.0.0 keeps its copies, so both
	apps would hook Sales Invoice.on_submit and send the same invoice to TRA twice.
	"""
	if RETIRED_APP not in frappe.get_installed_apps():
		return

	duplicated = [
		hook
		for hook in ("doc_events", "scheduler_events", "doctype_js")
		if frappe.get_hooks(hook, app_name=RETIRED_APP)
	]
	if not duplicated:
		return

	frappe.throw(
		_(
			"The installed vfd_providers still registers {0}, which csf_tz now owns. Migrating would"
			" send every invoice to TRA twice.<br><br>"
			"Update vfd_providers to 16.0.0 or later, or uninstall it, then migrate again."
		).format(", ".join(duplicated)),
		title=_("Duplicate VFD Handlers"),
	)
