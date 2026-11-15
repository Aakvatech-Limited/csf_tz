// Copyright (c) 2021, Aakvatech and contributors
// For license information, please see license.txt

// The Import File form is intentionally lightweight. Accounting document
// integrations are handled by the existing csf_tz landed-cost hooks.
frappe.ui.form.on("Import File", {
	refresh(frm) {
		// Reserved for Import File-specific UI actions.
	},
});
