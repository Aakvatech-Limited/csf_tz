import frappe
from frappe import _, bold
from frappe.utils import cint, flt
from hrms.hr.doctype.leave_encashment.leave_encashment import (
    LeaveEncashment as HRMSLeaveEncashment,
)


def validate_flags(doc, method=None):
    """Validate and auto-set is_deduction/is_earning flags."""
    if not _has_flag_fields(doc):
        return

    doc.is_deduction = cint(doc.is_deduction)
    doc.is_earning = cint(doc.is_earning)

    _auto_select_flags(doc)
    _ensure_valid_selection(doc)


def ensure_selection_before_submit(doc, method=None):
    validate_flags(doc)

    if not (getattr(doc, "is_deduction", 0) or getattr(doc, "is_earning", 0)):
        frappe.throw(
            _("Please select either Is Deduction or Is Earning before submitting.")
        )


def _has_flag_fields(doc):
    return hasattr(doc, "is_deduction") and hasattr(doc, "is_earning")


def _auto_select_flags(doc):
    days = flt(getattr(doc, "encashment_days", 0))
    amount = flt(getattr(doc, "encashment_amount", 0))

    if days < 0 or (not days and amount < 0):
        doc.is_deduction = 1
        doc.is_earning = 0
    elif days > 0 or amount > 0:
        doc.is_deduction = 0
        doc.is_earning = 1


def _ensure_valid_selection(doc):
    if getattr(doc, "is_deduction", 0) and getattr(doc, "is_earning", 0):
        frappe.throw(_("Select either Is Deduction or Is Earning, not both."))


def _get_salary_component(doc, purpose):
    if purpose == "deduction":
        doc_fields = ["deduction_salary_component", "salary_component_deduction"]
        leave_type_fields = [
            "deduction_component",
            "deduction_salary_component",
            "leave_encashment_deduction_component",
        ]
    else:
        doc_fields = ["earning_salary_component", "salary_component_earning"]
        leave_type_fields = ["earning_salary_component", "earning_component"]

    component = _get_value_from_fields(doc, doc_fields)
    if component:
        return component, _("Leave Encashment")

    component = _get_leave_type_value(doc.leave_type, leave_type_fields)
    if component:
        return component, _("Leave Type {0}").format(doc.leave_type)

    source = (
        _("Leave Encashment")
        if _has_any_field(doc, doc_fields)
        else _("Leave Type {0}").format(doc.leave_type)
    )
    return None, source


def _get_value_from_fields(doc, fieldnames):
    """Get first non-empty value from doc fields."""
    for field in fieldnames:
        if hasattr(doc, field):
            value = getattr(doc, field)
            if value:
                return value
    return None


def _get_leave_type_value(leave_type, fieldnames):
    """Get first non-empty value from leave type fields."""
    for field in fieldnames:
        if frappe.db.has_column("Leave Type", field):
            value = frappe.db.get_value("Leave Type", leave_type, field)
            if value:
                return value
    return None


def _has_any_field(doc, fieldnames):
    """Check if doc has any of the specified fields."""
    return any(hasattr(doc, field) for field in fieldnames)


_original_before_submit = HRMSLeaveEncashment.before_submit
_original_on_submit = HRMSLeaveEncashment.on_submit


def _custom_before_submit(self):
    """Custom before_submit to allow negative amounts for deductions."""
    if self.encashment_amount is None:
        frappe.throw(_("Encashment amount is required"))

    amount = flt(self.encashment_amount)

    if _has_flag_fields(self):
        validate_flags(self)

        if self.is_deduction and amount < 0:
            return

        # Allow positive amounts for earnings
        if self.is_earning and amount > 0:
            # Call original validation for positive amounts
            return _original_before_submit(self)

        # Zero or mismatched amounts
        if (
            amount == 0
            or (self.is_deduction and amount > 0)
            or (self.is_earning and amount < 0)
        ):
            frappe.throw(_("Invalid amount for selected encashment type"))
    else:
        # Standard behavior - only positive amounts
        return _original_before_submit(self)


def _custom_on_submit(self):
    """Custom on_submit to handle deductions and earnings."""
    # Handle custom flags if present
    if _has_flag_fields(self):
        _create_custom_additional_salary(self)
    else:
        # Use original behavior
        _original_on_submit(self)


def _create_custom_additional_salary(doc):
    """Create additional salary for deduction or earning."""
    is_deduction = cint(getattr(doc, "is_deduction", 0))
    component_type = "deduction" if is_deduction else "earning"

    # Get salary component
    component, source = _get_salary_component(doc, component_type)
    if not component:
        frappe.throw(
            _(
                "Please set a {0} Component on Leave Type {1} "
                "or specify it on the Leave Encashment."
            ).format(_("Deduction") if is_deduction else _("Earning"), doc.leave_type)
        )

    # Create additional salary
    additional_salary = frappe.new_doc("Additional Salary")
    additional_salary.company = doc.company or frappe.get_value(
        "Employee", doc.employee, "company"
    )
    additional_salary.employee = doc.employee
    additional_salary.currency = doc.currency
    additional_salary.salary_component = component
    additional_salary.type = "Deduction" if is_deduction else "Earning"
    additional_salary.payroll_date = doc.encashment_date
    additional_salary.amount = abs(flt(doc.encashment_amount))
    additional_salary.overwrite_salary_structure_amount = 0
    additional_salary.ref_doctype = doc.doctype
    additional_salary.ref_docname = doc.name
    additional_salary.submit()

    doc.additional_salary = additional_salary.name
    doc.db_set("additional_salary", additional_salary.name)


# Apply monkey patches
HRMSLeaveEncashment.before_submit = _custom_before_submit
HRMSLeaveEncashment.on_submit = _custom_on_submit
