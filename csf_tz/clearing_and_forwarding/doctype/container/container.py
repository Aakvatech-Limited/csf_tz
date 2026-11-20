# -*- coding: utf-8 -*-
# Copyright (c) 2019, Bravo Logisitcs and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class Container(Document):
    pass


@frappe.whitelist()
def remove_booking(**args):
    args = frappe._dict(args)

    doc_list = frappe.get_list(
        "Container",
        filters={"booking_number": args.booking_number, "export_reference": args.name},
    )

    for ref in doc_list:
        doc = frappe.get_doc("Container", ref.name)
        doc.db_set("export_reference", "")
        doc.db_set("seal_number", "")
        doc.db_set("number_of_bundles", 0)
        doc.db_set("gross_weight", 0.0)
        doc.db_set("net_weight", 0.0)
        doc.db_set("parenttype", "")
        doc.db_set("parent", "")
        doc.db_set("parentfield", "")
        doc.save()

        doc_list2 = frappe.get_list(
            "Container Seals",
            filters={
                "booking_number": args.booking_number,
                "export_reference": args.name,
            },
        )

        for ref in doc_list2:
            doc = frappe.get_doc("Container Seals", ref.name)
            doc.db_set("export_reference", "")
            doc.db_set("parenttype", "")
            doc.db_set("parent", "")
            doc.db_set("parentfield", "")
            doc.db_set("container_no", "")
            doc.save()
