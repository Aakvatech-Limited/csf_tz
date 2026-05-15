frappe.ui.form.on('Student Applicant', {
	onload: function(frm) {
		frm.trigger("setup_btns");
	},
	refresh: function(frm) {
		frm.trigger("setup_btns");
	},
	setup_btns: function(frm) {
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
	setup: function(frm) {
		frappe.db.get_value('Fee Structure', frm.doc.fee_structure, ["company"], function(value1) {
			frappe.db.get_value('Company', value1.company, ["send_fee_details_to_bank"], function(value2) {
				frm.send_fee_details_to_bank = value2.send_fee_details_to_bank || 0;

			});
		});
    },

});
