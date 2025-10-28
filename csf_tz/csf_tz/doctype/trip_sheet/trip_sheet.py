# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.model.document import Document


class TripSheet(Document):
    def validate(self):
        # If status set to Completed in form, ensure required fields are present.
        if getattr(self, "status", None) == "Completed":
            if not getattr(self, "end_km", None):
                frappe.throw(_("End KM must be filled when status is 'Completed'."))
            if not getattr(self, "fuel_consumed", None):
                frappe.throw(_("Fuel Consumed must be filled when status is 'Completed'."))

    def before_submit(self):
        # Final checks before submit
        if getattr(self, "status", None) != "Completed":
            frappe.throw(_("Trip status must be 'Completed' before submitting."))
        if not getattr(self, "end_km", None):
            frappe.throw(_("End KM must be filled before submitting."))
        if not getattr(self, "fuel_consumed", None):
            frappe.throw(_("Fuel Consumed must be filled before submitting."))

    def before_save(self):
        # Keep item_reference in sync on save
        self.set_item_reference_table()

    def set_item_reference_table(self):
        """
        Rebuild the item_reference child table from trip_sheet_reference child table.
        Uses fields:
          - trip_sheet_reference[].reference_doctype
          - trip_sheet_reference[].reference_document
        Appends rows to item_reference with fields:
          - reference_doctype
          - reference_document_id
          - item_name
          - qty
          - amount
        """
        self.set("item_reference", [])

        for row in self.get("trip_sheet_reference") or []:
            ref_doctype = row.get("reference_doctype")
            ref_doc = row.get("reference_document")
            if not (ref_doctype and ref_doc):
                continue

            items = get_reference_items(ref_doctype, ref_doc) or []
            for it in items:
                self.append("item_reference", {
                    "reference_doctype": ref_doctype,
                    "reference_document_id": ref_doc,
                    "item_name": it.get("item_name") or "",
                    "qty": it.get("qty") or 0,
                    "amount": it.get("amount") or 0,
                })


@frappe.whitelist()
def get_reference_items(reference_doctype, reference_document):
    """
    Return list of dicts: { item_name, qty, amount } for the given reference.
    Accepts reference_document (string id) to match JS.
    """
    items = []
    if reference_doctype not in [
        "Purchase Order",
        "Delivery Note",
        "Purchase Receipt",
        "Purchase Invoice",
        "Sales Order",
        "Stock Entry",
    ]:
        return items

    try:
        doc = frappe.get_doc(reference_doctype, reference_document)
    except Exception:
        return items

    for i in getattr(doc, "items", []) or []:
        amount = getattr(i, "amount", None)
        if amount is None:
            amount = getattr(i, "base_amount", None)
        # qty fallback: qty or transfer_qty or delivered_qty
        qty = getattr(i, "qty", None)
        if qty is None:
            qty = getattr(i, "transfer_qty", None)
        if qty is None:
            qty = getattr(i, "delivered_qty", 0)
        item_name = getattr(i, "item_name", None) or getattr(i, "item_code", "")

        items.append({
            "item_name": item_name,
            "qty": qty or 0,
            "amount": amount or 0
        })

    return items
