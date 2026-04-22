import frappe


REPORTS_TO_REMOVE = {
	"Salary Register csf",
	"Salary Register CTC",
	"Salary Register Summary",
	"Salary Register Summary with Components",
	"Salary Register Summary with Monthly Comparison",
}


def execute():
	if not frappe.db.exists("Workspace", "Tanzania"):
		return

	link_names = frappe.get_all(
		"Workspace Link",
		filters={
			"parenttype": "Workspace",
			"parent": "Tanzania",
			"link_to": ["in", tuple(REPORTS_TO_REMOVE)],
		},
		pluck="name",
	)

	for link_name in link_names:
		frappe.db.delete("Workspace Link", {"name": link_name})

	card_break = frappe.get_all(
		"Workspace Link",
		filters={
			"parenttype": "Workspace",
			"parent": "Tanzania",
			"type": "Card Break",
			"label": "Payroll Reports",
		},
		pluck="name",
		limit=1,
	)
	if card_break:
		frappe.db.set_value("Workspace Link", card_break[0], "link_count", 5, update_modified=False)

	if link_names or card_break:
		frappe.db.commit()
