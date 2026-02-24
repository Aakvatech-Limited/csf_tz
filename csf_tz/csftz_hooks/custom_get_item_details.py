# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
import frappe
from erpnext.stock.get_item_details import get_item_details

@frappe.whitelist()
def custom_get_item_details(args, doc=None, for_validate=False, overwrite_warehouse=True):
    
    # Call the original get_item_details method
    response = get_item_details(args, doc, for_validate, overwrite_warehouse)

    # Check CSF TZ Settings
    override_sales_invoice_qty = frappe.db.get_single_value("CSF TZ Settings", "override_sales_invoice_qty")

    # If the setting is enabled, remove the qty field from the response
    if override_sales_invoice_qty:
        response.pop("qty", None)  

    return response
