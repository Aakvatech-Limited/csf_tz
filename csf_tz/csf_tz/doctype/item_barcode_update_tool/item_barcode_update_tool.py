# Copyright (c) 2022, Aakvatech and contributors
# For license information, please see license.txt

from frappe import _
import frappe
from frappe.model.document import Document


class ItemBarcodeUpdateTool(Document):
    pass


@frappe.whitelist()
def update_barcodes(doc):
    import json

    if isinstance(doc, str):
        doc = frappe._dict(json.loads(doc))
    else:
        return
    if not doc.barcodes:
        return
    item = frappe.get_doc("Item", doc.item_code)
    item.barcodes = []
    item.save(ignore_permissions=True)
    item.reload()
    for barcode in doc.barcodes:
        item.append(
            "barcodes",
            {
                "barcode": barcode["barcode"],
                "barcode_type": barcode["barcode_type"],
                "uom": barcode["uom"],
            },
        )
    item.save(ignore_permissions=True)
    frappe.db.commit()
    frappe.msgprint(
        _("Barcodes successfully updated for Item: " + item.item_name), alert=True
    )

    return item
