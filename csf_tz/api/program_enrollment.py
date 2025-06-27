from __future__ import unicode_literals
import frappe
from frappe import _
from education.education.doctype.program_enrollment.program_enrollment import ProgramEnrollment
# from csf_tz import console


def create_course_enrollments(self):
    student = frappe.get_doc("Student", self.student)
    program = frappe.get_doc("Program", self.program)
    course_list = [course.course for course in program.courses]
    for course_name in course_list:
        student.enroll_in_course(
            course_name=course_name, program_enrollment=self.name)


def create_course_enrollments_override(doc, method):
    ProgramEnrollment.create_course_enrollments = create_course_enrollments


@frappe.whitelist()
def get_fee_schedule(program, academic_year, academic_term=None, student_category=None):
    """Returns Fee Schedule.

    :param program: Program.
    :param student_category: Student Category   
    :param academic_year
    :param academic_term
    """
    fs = frappe.get_list("Program Fee", fields=["academic_term", "fee_structure", "due_date", "amount"],
                         filters={"parent": program, "student_category": student_category}, parent_doctype="Program Enrollment", order_by="idx")

    fees_list = []
    for i in fs:
        fs_academic_year = frappe.get_value(
            "Fee Structure", i["fee_structure"], "academic_year") or ""
        fs_academic_term = "False"
        if academic_term:
            fs_academic_term = frappe.get_value(
                "Fee Structure", i["fee_structure"], "academic_term") or ""
        if fs_academic_term != "False":
            if fs_academic_term == academic_term and fs_academic_year == academic_year:
                fees_list.append(i)
        else:
            if fs_academic_year == academic_year:
                fees_list.append(i)

    return fees_list


def validate_submit_program_enrollment(doc, method):
    if not doc.student_category:
        frappe.throw(_("Please set Student Category"))
