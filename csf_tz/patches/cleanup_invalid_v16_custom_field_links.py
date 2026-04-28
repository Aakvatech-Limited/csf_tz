import frappe


def execute():
    for field_name in (
        "Journal Entry-expense_record",
        "Purchase Invoice-expense_record",
        "Stock Entry-repack_template",
        "Stock Entry-transfer_goods_between_company",
    ):
        frappe.delete_doc_if_exists("Custom Field", field_name, force=True)
