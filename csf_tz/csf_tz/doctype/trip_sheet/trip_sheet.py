# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.model.document import Document


class TripSheet(Document):
    # validate required fields when status is Completed (before submit)
    def validate(self):
        # If user sets status to Completed while still in draft/state before submit,
        # ensure required fields are present.
        if self.status == "Completed":
            if not self.end_km:
                frappe.throw(_("End KM must be filled when status is 'Completed'."))
            if not self.fuel_consumed:
                frappe.throw(_("Fuel Consumed must be filled when status is 'Completed'."))

    def before_submit(self):
        # Final checks before submit
        if self.status != "Completed":
            frappe.throw(_("Trip status must be 'Completed' before submitting."))
        if not self.end_km:
            frappe.throw(_("End KM must be filled before submitting."))
        if not self.fuel_consumed:
            frappe.throw(_("Fuel Consumed must be filled before submitting."))

    # Keep item_reference in sync on save: populate from delivery_note child table
    def before_save(self):
        self.set_item_reference_table()

    def set_item_reference_table(self):
        # Rebuild the item_reference child table from delivery_note child table.
        # This ensures removal of references in delivery_note is reflected here.
        self.set("item_reference", [])

        for row in self.get("delivery_note") or []:
            # Use the actual field names in delivery_note child table:
            # - reference_doctype (Select)
            # - reference_document (Dynamic Link / Link)
            if row.get("reference_doctype") and row.get("reference_document"):
                items = get_reference_items(row.reference_doctype, row.reference_document)
                for item in items:
                    self.append("item_reference", {
                        "reference_doctype": row.reference_doctype,
                        "reference_document_id": row.reference_document,
                        "item_name": item.get("item_name"),
                        "qty": item.get("qty"),
                        "amount": item.get("amount"),
                    })


@frappe.whitelist()
def get_reference_items(reference_doctype, reference_document):
    """
    Return a list of items for the given reference document.
    Each item is a dict with keys: item_name, qty, amount
    """
    items = []
    if reference_doctype in [
        "Purchase Order",
        "Delivery Note",
        "Purchase Receipt",
        "Purchase Invoice",
        "Sales Order",
        "Stock Entry",
    ]:
        try:
            doc = frappe.get_doc(reference_doctype, reference_document)
        except frappe.DoesNotExistError:
            return items

        for i in getattr(doc, "items", []) or []:
            # derive amount if available, fallback to base_amount or 0
            amount = getattr(i, "amount", None)
            if amount is None:
                amount = getattr(i, "base_amount", 0)
            items.append({
                "item_name": getattr(i, "item_name", getattr(i, "item_code", "")),
                "qty": getattr(i, "qty", getattr(i, "transfer_qty", 0)),
                "amount": amount or 0,
            })
    return items
