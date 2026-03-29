import frappe
from frappe import _


@frappe.whitelist()
def get_custom_filters(reference_doctype):
    try:
        # Check for enabled custom filters
        custom_filters = frappe.get_all(
            "CSF TZ Custom Filters",
            filters={"is_enabled": 1, "reference_doctype": reference_doctype},
            fields=["name", "reference_doctype_field"],
        )

        # If no filters are found, return an empty list
        if not custom_filters:
            return []

        filters_list = []
        for filter_doc in custom_filters:
            # Fetch filter rules for each enabled custom filter
            filter_rules = frappe.get_all(
                "CSF TZ Custom Filters Rules",
                filters={"parent": filter_doc.name},
                fields=["doctype_field_name", "filter_condition", "filter_value"],
            )

            # Append each rule to the filter list
            for rule in filter_rules:
                filters_list.append(
                    [
                        filter_doc.reference_doctype_field,  # Example: Employee
                        rule.doctype_field_name,  # Example: status
                        rule.filter_condition,  # Example: =
                        rule.filter_value,  # Example: Active
                    ]
                )

        return filters_list
    except Exception as e:
        frappe.log_error(f"Error fetching custom filters: {str(e)}")
        return []
