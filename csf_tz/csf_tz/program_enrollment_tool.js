frappe.ui.form.on("Program Enrollment Tool", {
    refresh: function (frm) {
        frm.toggle_display(['enroll_students']);
    },
    academic_year: function (frm) {
        frm.toggle_display("enroll_students", is_viewable);
    },
    get_students: function (frm) {
        if (frm.doc.students.length > 0) {
            frm.add_custom_button(__("Enroll All Students"), function () {
                if (frm.doc.students.length > 0) {
                    frappe.call({
                        method: "csf_tz.custom_api.enroll_all_students",
                        args: {
                            "self": frm.doc
                        },
                        callback: function (r) {
                            if (r.message === 'queued') {
                                frappe.show_alert({
                                    message: __("Students enrollment has been queued."),
                                    indicator: 'orange'
                                });
                            } else {
                                frappe.show_alert({
                                    message: __("{0} students enrolled.", [r.message]),
                                    indicator: 'green'
                                });
                            }
                        }
                    });
                } else {
                    frappe.msgprint(__("No students to enroll"))
                }
            })
        }
    },

})
