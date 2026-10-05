frappe.ui.form.on('Student Applicant', {
	refresh: function(frm) {
		frm.trigger("setup_btns");
	},
	setup_btns: function(frm) {
		if (frm.doc.__islocal || !frm.doc.fee_structure) {
			return;
		}
		// the company's "Send Fee details to Bank" setting is fetched once per fee structure;
		// buttons are drawn again when it arrives, otherwise they would never show on first load
		if (frm.bank_setting_for !== frm.doc.fee_structure) {
			frm.bank_setting_for = frm.doc.fee_structure;
			frm.send_fee_details_to_bank = 0;
			frappe.db.get_value('Fee Structure', frm.doc.fee_structure, 'company')
				.then(r => {
					const company = r.message && r.message.company;
					return company ? frappe.db.get_value('Company', company, 'send_fee_details_to_bank') : null;
				})
				.then(r => {
					frm.send_fee_details_to_bank = (r && r.message && r.message.send_fee_details_to_bank) || 0;
					if (frm.send_fee_details_to_bank) {
						frm.trigger("setup_btns");
					}
				});
			return;
		}
		if (!frm.send_fee_details_to_bank) {
			return;
		}
		if(frm.doc.docstatus == 1 && frm.doc.application_status != "Approved") {
			frm.clear_custom_buttons();
			if(frm.doc.application_status == "Applied") {
				frm.add_custom_button(__("Reject"), function() {
					frm.set_value("application_status", "Rejected");
					frm.save_or_update();
				}, 'Student Applicant Actions');
			}
			if(["Applied", "Rejected"].includes(frm.doc.application_status)) {
				frm.add_custom_button(__("Awaiting Registration Fees"), function() {
					frm.set_value("application_status", "Awaiting Registration Fees");
					frm.save_or_update();
				}, 'Student Applicant Actions');
			}
		}
	},
});