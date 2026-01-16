import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    fields = {
        "Sales Invoice Item": [
            {
                "fieldname": "custom_trade_in_details",
                "fieldtype": "Section Break",
                "insert_after": "page_break",
                "label": "Trade In Details",
                "depnds_on": "eval:doc.item_code == \"Trade In\"",
               
            },
            {
                "fieldname": "custom_trade_in_item",
                "fieldtype": "Link",
                "insert_after": "custom_trade_in_details",
                "label": "Item",
                "options": "Item",
                "mandatory_depends_on": "eval:doc.item_code == \"Trade In\"",
                "no_copy": 1
            },
            {
                "fieldname": "custom_trade_in_qty",
                "fieldtype": "Float",
                "insert_after": "custom_trade_in_item",
                "label": "Qty",
                "mandatory_depends_on": "eval:doc.item_code == \"Trade In\"",
                "no_copy": 1
            },
            {
                "fieldname": "custom_trade_in_uom",
                "fieldtype": "Link",
                "insert_after": "custom_trade_in_qty",
                "label": "Trade In UOM",
                "options": "UOM",
                "no_copy": 1
            },
            {
                "fieldname": "custom_trade_in_column",
                "fieldtype": "Column Break",
                "insert_after": "custom_trade_in_uom",
                "label": None,
            },
            {
                "fieldname": "custom_trade_in_incoming_rate",
                "fieldtype": "Currency",
                "insert_after": "custom_trade_in_column",
                "label": "Incoming Rate",
                "mandatory_depends_on": "eval:doc.item_code == \"Trade In\"",
                "no_copy": 1
            },
            {
                "fieldname": "custom_total_trade_in_value",
                "fieldtype": "Currency",
                "insert_after": "custom_trade_in_incoming_rate",
                "label": "Total Trade In Value",
                "read_only": 1,
                "no_copy": 1
            },
            {
                "fieldname": "custom_trade_in_batch_no",
                "fieldtype": "Data",
                "insert_after": "custom_total_trade_in_value",
                "label": "Trade In Batch No",
                "no_copy": 1
            },
            {
                "fieldname": "custom_trade_in_serial_no",
                "fieldtype": "Small Text",
                "insert_after": "custom_trade_in_batch_no",
                "label": "Trade In Serial No",
                "no_copy": 1
            },
   {
                "fieldname": "custom_uom",
                "fieldtype": "Link",
                "insert_after": "item_code",
                "label": "UOM",
                "options": "UOM",
                "no_copy": 1,
                "fetch_from": "item_code.stock_uom",
                "depends_on": "eval:doc.item_code == \"Trade In\"",
            },
        ],
        "Sales Invoice": [
            {
                "fieldname": "custom_is_trade_in",
                "fieldtype": "Check",
                "insert_after": "update_stock",
                "label": "Is Trade In",
                "depends_on": "eval:doc.customer",
                "no_copy": 1
            }
        ],
         "Stock Entry": [
            {
                "fieldname": "custom_sales_invoice",
                "fieldtype": "Link",
                "options": "Sales Invoice",
                "insert_after": "stock_entry_type",
                "label": "Sales Invoice",
                "depends_on": "eval:doc.stock_entry_type == 'Material Receipt'",
                "no_copy": 1
            }
        ],
        "Company": [
            {
                "fieldname": "custom_trade_in_settings",
                "fieldtype": "Section Break",
                "insert_after": "total_monthly_sales",
                "label": "Trade In Settings",
            },
            {
                "fieldname": "custom_trade_in_sales_percentage",
                "fieldtype": "Percent",
                "insert_after": "total_monthly_sales",
                "label": "Trade In Sales Percentage",
                "precision": "2",
            },
            {
                "fieldname": "custom_trade_in_control_account",
                "fieldtype": "Link",
                "insert_after": "custom_trade_in_sales_percentage",
                "label": "Trade In Control Account",
                "options": "Account",
            }
        ]
    }

    create_custom_fields(fields, update=True)