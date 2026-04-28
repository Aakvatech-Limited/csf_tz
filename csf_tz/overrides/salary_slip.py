import frappe
from frappe import _
from frappe.utils.background_jobs import enqueue

try:
    from hrms.payroll.doctype.salary_slip.salary_slip import (
        SalarySlip as _SalarySlip,
    )  # version-14

except ImportError:
    from erpnext.payroll.doctype.salary_slip.salary_slip import (
        SalarySlip as _SalarySlip,
    )  # version-13


class SalarySlip(_SalarySlip):
    def get_working_days_details(self, *args, **kwargs):
        result = super().get_working_days_details(*args, **kwargs)

        fixed_working_days = get_fixed_working_days()
        if fixed_working_days is None:
            return result

        self.total_working_days = min(fixed_working_days, self.total_working_days)
        self.payment_days = min(fixed_working_days, self.payment_days)
        return result

    def calculate_lwp_or_ppl_based_on_leave_application(
        self, holidays, working_days, *args, **kwargs
    ):
        fixed_working_days = get_fixed_working_days()
        if fixed_working_days is not None:
            working_days = min(fixed_working_days, working_days)

        return super().calculate_lwp_or_ppl_based_on_leave_application(
            holidays, working_days, *args, **kwargs
        )

    def get_payment_days(self, *args, **kwargs):
        fixed_working_days = get_fixed_working_days()
        if fixed_working_days is None:
            return super().get_payment_days(*args, **kwargs)

        self.total_working_days = min(fixed_working_days, self.total_working_days)
        payment_days = super().get_payment_days(*args, **kwargs)
        return min(fixed_working_days, payment_days)

    def email_salary_slip(self):
        csf_tz_settings = frappe.get_cached_doc("CSF TZ Settings", "CSF TZ Settings")
        if not csf_tz_settings.override_salary_slip_email_message:
            return super().email_salary_slip()

        receiver = frappe.db.get_value("Employee", self.employee, "prefered_email")
        payroll_settings = frappe.get_single("Payroll Settings")
        message = csf_tz_settings.salary_slip_email_message

        password = None
        if payroll_settings.encrypt_salary_slips_in_emails:
            password = generate_password_for_pdf(
                payroll_settings.password_policy, self.employee
            )
            message += """<br>Note: Your salary slip is password protected,
				the password to unlock the PDF is of the format {0}. """.format(
                payroll_settings.password_policy
            )

        if receiver:
            email_args = {
                "sender": payroll_settings.sender_email,
                "recipients": [receiver],
                "message": _(message),
                "subject": "Salary Slip - from {0} to {1}".format(
                    self.start_date, self.end_date
                ),
                "attachments": [
                    frappe.attach_print(
                        self.doctype, self.name, file_name=self.name, password=password
                    )
                ],
                "reference_doctype": self.doctype,
                "reference_name": self.name,
            }
            if not frappe.in_test:
                enqueue(
                    method=frappe.sendmail,
                    queue="short",
                    timeout=300,
                    is_async=True,
                    **email_args,
                )
            else:
                frappe.sendmail(**email_args)
        else:
            frappe.msgprint(
                _(
                    f"{self.employee_name}: Employee email not found, hence email not sent"
                )
            )


def get_fixed_working_days():
    csf_tz_settings = frappe.get_cached_doc("CSF TZ Settings", "CSF TZ Settings")
    if csf_tz_settings.enable_fixed_working_days_per_month:
        return csf_tz_settings.working_days_per_month


def generate_password_for_pdf(policy_template, employee):
    employee = frappe.get_doc("Employee", employee)
    return policy_template.format(**employee.as_dict())
