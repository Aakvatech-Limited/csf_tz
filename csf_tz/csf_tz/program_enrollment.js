frappe.ui.form.on("Program Enrollment", {
    program: function (frm) {
        frm.set_value("fees", "");
        frm.events.get_courses(frm);
        if (frm.doc.program) {
            frappe.call({
                method: "csf_tz.api.program_enrollment.get_fee_schedule",
                args: {
                    "program": frm.doc.program,
                    "student_category": frm.doc.student_category,
                    "academic_year": frm.doc.academic_year,
                    "academic_term": frm.doc.academic_term
                },
                async: false,
                callback: function (r) {
                    if (r.message) {
                        frm.set_value("fees", r.message);
                        frm.events.get_courses(frm);
                    }
                }
            });
        }
    },

    student_category: function () {
        frappe.ui.form.trigger("program");
    },
    
    validate: function (frm) {
        if (( !frm.doc.fees || !frm.doc.fees.length) && frm.doc.student_category) {
            frm.trigger("program");
        }
    }
});
