import frappe
from frappe import _, bold
from frappe.utils import cint, flt

from hrms.hr.doctype.leave_encashment.leave_encashment import LeaveEncashment as HRMSLeaveEncashment


def validate_flags(doc, method=None):
	if not _has_flag_fields(doc):
		return

	doc.is_deduction = cint(doc.is_deduction)
	doc.is_earning = cint(doc.is_earning)

	_auto_select_flags(doc)
	_ensure_valid_selection(doc)


def ensure_selection_before_submit(doc, method=None):
	validate_flags(doc)

	if not (getattr(doc, "is_deduction", 0) or getattr(doc, "is_earning", 0)):
		frappe.throw(_("Please select either Is Deduction or Is Earning before submitting."))


def _has_flag_fields(doc):
	return hasattr(doc, "is_deduction") and hasattr(doc, "is_earning")


def _ensure_valid_selection(doc):
	if getattr(doc, "is_deduction", 0) and getattr(doc, "is_earning", 0):
		frappe.throw(_("Select either Is Deduction or Is Earning, not both."))


def _auto_select_flags(doc):
	days = flt(getattr(doc, "encashment_days", 0))
	amount = flt(getattr(doc, "encashment_amount", 0))

	if days < 0 or (not days and amount < 0):
		doc.is_deduction = 1
		doc.is_earning = 0
	elif days > 0 or amount > 0:
		doc.is_deduction = 0
		doc.is_earning = 1


def _doc_has_fields(doc, fieldnames):
	for field in fieldnames:
		if hasattr(doc, field):
			return True
	return False


def _get_salary_component_from_doc(doc, fieldnames):
	for field in fieldnames:
		if hasattr(doc, field):
			value = getattr(doc, field)
			if value:
				return value
	return None


def _get_salary_component_from_leave_type(leave_type, fieldnames):
	for field in fieldnames:
		if frappe.db.has_column("Leave Type", field):
			value = frappe.db.get_value("Leave Type", leave_type, field)
			if value:
				return value
	return None


def _ensure_salary_component(name, abbr, component_type):
	existing = frappe.db.exists("Salary Component", name)
	if existing:
		current_type = frappe.db.get_value("Salary Component", name, "type")
		if current_type != component_type:
			frappe.db.set_value("Salary Component", name, "type", component_type)
		return name

	doc = frappe.get_doc(
		{
			"doctype": "Salary Component",
			"salary_component": name,
			"salary_component_abbr": abbr,
			"type": component_type,
			"depends_on_payment_days": 0,
			"statistical_component": 0,
			"do_not_include_in_total": 0,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _get_default_salary_component(purpose):
	expected_type = "Deduction" if purpose == "deduction" else "Earning"

	candidates = (
		["Leave Encashment Deduction", "Leave Encashment - Deduction", "Leave Encashment (Deduction)"]
		if purpose == "deduction"
		else ["Leave Encashment"]
	)

	for candidate in candidates:
		if frappe.db.exists("Salary Component", {"name": candidate, "type": expected_type}):
			return candidate

	if purpose == "deduction":
		return _ensure_salary_component("Leave Encashment Deduction", "LED", expected_type)

	if frappe.db.exists("Salary Component", {"name": "Leave Encashment", "type": expected_type}):
		return "Leave Encashment"

	return _ensure_salary_component("Leave Encashment", "LE", expected_type)


def _get_salary_component(doc, purpose):
	if purpose == "deduction":
		doc_fields = ["deduction_salary_component", "salary_component_deduction"]
		leave_type_fields = ["deduction_salary_component", "deduction_component", "leave_encashment_deduction_component"]
	else:
		doc_fields = ["earning_salary_component", "salary_component_earning"]
		leave_type_fields = ["earning_salary_component", "earning_component"]

	component = _get_salary_component_from_doc(doc, doc_fields)
	if component:
		return component, _("Leave Encashment")

	component = _get_salary_component_from_leave_type(doc.leave_type, leave_type_fields)
	if component:
		return component, _("Leave Type {0}").format(doc.leave_type)

	source = _("Leave Encashment") if _doc_has_fields(doc, doc_fields) else _("Leave Type {0}").format(doc.leave_type)
	return None, source


_original_create_additional_salary = HRMSLeaveEncashment.create_additional_salary
_original_before_submit = HRMSLeaveEncashment.before_submit


def _custom_create_additional_salary(self):
	if not _has_flag_fields(self):
		return _original_create_additional_salary(self)

	is_deduction = cint(getattr(self, "is_deduction", 0))
	is_earning_flag = cint(getattr(self, "is_earning", 0))

	if is_deduction and is_earning_flag:
		frappe.throw(_("Select either Is Deduction or Is Earning, not both."))

	if not is_deduction and not is_earning_flag:
		return _original_create_additional_salary(self)

	component_type = "deduction" if is_deduction else "earning"
	component, source = _get_salary_component(self, component_type)

	if not component:
		default_component = _get_default_salary_component(component_type)
		if default_component:
			component = default_component
			source = _("Default Salary Component")
		else:
			raise_msg = _("Please set a Salary Component for {0} on {1}.").format(
				_("Deduction") if component_type == "deduction" else _("Earning"),
				source,
			)
			frappe.throw(raise_msg)

	raw_amount = flt(self.encashment_amount)
	amount = abs(raw_amount)

	additional_salary = frappe.new_doc("Additional Salary")
	additional_salary.company = self.company or frappe.get_value("Employee", self.employee, "company")
	additional_salary.employee = self.employee
	additional_salary.currency = self.currency
	additional_salary.salary_component = component
	additional_salary.type = "Deduction" if is_deduction else "Earning"
	additional_salary.payroll_date = self.encashment_date
	additional_salary.amount = amount
	additional_salary.overwrite_salary_structure_amount = 0
	additional_salary.ref_doctype = self.doctype
	additional_salary.ref_docname = self.name
	additional_salary.submit()

	self.additional_salary = additional_salary.name
	self.db_set("additional_salary", additional_salary.name)

	return additional_salary


HRMSLeaveEncashment.create_additional_salary = _custom_create_additional_salary


def _custom_before_submit(self):
	if self.encashment_amount is None:
		frappe.throw(_("Encashment amount is required before submitting."))

	amount = flt(self.encashment_amount)
	if _has_flag_fields(self):
		self.is_deduction = cint(getattr(self, "is_deduction", 0))
		self.is_earning = cint(getattr(self, "is_earning", 0))
		_auto_select_flags(self)
		_ensure_valid_selection(self)

		if not (self.is_deduction or self.is_earning):
			frappe.throw(_("Please select either Is Deduction or Is Earning before submitting."))

		if amount < 0 and not self.is_deduction:
			frappe.throw(_("Negative encashment requires {0} to be enabled.").format(bold(_("Is Deduction"))))

	if amount > 0:
		return _original_before_submit(self)


HRMSLeaveEncashment.before_submit = _custom_before_submit
