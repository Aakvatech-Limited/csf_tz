import frappe


def execute():
    for field_name in (
        "Customer-is_authotp_applied",
        "Customer-default_authotp_method",
        "Customer-authotp_validated",
        "Sales Invoice-authotp",
        "Sales Invoice-authotp_method",
        "Sales Invoice-column_break_sn02w",
        "Sales Invoice-authotp_validated",
    ):
        frappe.delete_doc_if_exists("Custom Field", field_name, force=True)

    if frappe.db.exists("Custom Field", "Sales Invoice-vfd_details"):
        frappe.db.set_value(
            "Custom Field",
            "Sales Invoice-vfd_details",
            "insert_after",
            "generate_vfd",
        )
