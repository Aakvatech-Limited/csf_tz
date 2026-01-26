from hrms.hr.doctype.leave_encashment.leave_encashment import (
    LeaveEncashment as HRMSLeaveEncashment,
)

from csf_tz.csftz_hooks import leave_encashment as le_hooks


class LeaveEncashment(HRMSLeaveEncashment):
    def before_submit(self):
        # Reuse existing custom logic that allows deductions/negative amounts
        le_hooks._custom_before_submit(self)

    def on_submit(self):
        # Create Additional Salary using the custom deduction/earning handling
        le_hooks._custom_on_submit(self)
