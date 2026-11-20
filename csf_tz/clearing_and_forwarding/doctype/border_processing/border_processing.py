# -*- coding: utf-8 -*-
# Copyright (c) 2019, Bravo Logisitcs and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document

from csf_tz.after_sales_services.doctype.requested_payments.requested_payments import (
    validate_requested_funds,
)


class BorderProcessing(Document):
    from csf_tz.after_sales_services.doctype.reference_payment_table.reference_payment_table import (
        update_child_table,
    )

    def before_save(self):
        validate_requested_funds(self)

    def onload(self):
        if not self.company:
            self.company = frappe.defaults.get_user_default(
                "Company"
            ) or frappe.defaults.get_global_default("company")


@frappe.whitelist()
def create_border_processing(**args):
    args = frappe._dict(args)

    existing_border_processing = frappe.db.get_value(
        "Border Processing", {"cross_border_no": args.cross_border_no}
    )

    if existing_border_processing:
        doc = frappe.get_doc("Border Processing", existing_border_processing)
        # doc.db_set("no_of_borders", args.number_of_borders)
        # doc.db_set("number_of_borders", args.number_of_borders)
        # doc.db_set("documents_received", args.documents_received_date)
        doc.db_set("customer", args.customer)
        return existing_border_processing
    else:
        new_border_processing = frappe.new_doc("Border Processing")
        new_border_processing.update(
            {
                "cross_border_no": args.cross_border_no,
                "reference_file": args.doctype,
                "creation_document_no": args.file_number,
                "customer": args.customer,
            }
        )
        new_border_processing.insert(ignore_permissions=True)
        return new_border_processing.name
