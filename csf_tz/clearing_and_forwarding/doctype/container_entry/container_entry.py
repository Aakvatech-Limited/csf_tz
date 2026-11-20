# -*- coding: utf-8 -*-
# Copyright (c) 2019, Bravo Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class ContainerEntry(Document):
    def on_submit(self):
        create_container(self)


@frappe.whitelist()
def create_container(doc):
    # check if container exists

    for value in doc.container_detail:
        new_container = frappe.new_doc("Container")
        new_container.update(
            {
                "reference_container_entry": doc.doctype,
                "creation_document_no": doc.name,
                "booking_number": doc.booking_number,
                "shipping_line": doc.shipping_line,
                "collection_date": doc.collection_date,
                "container_type": value.container_type,
                "container_size": value.container_size,
                "container_no": value.container_no,
                "parenttype": "Export",
                "parent": doc.export_reference,
                "parentfield": "container_information",
            }
        )
        new_container.insert(ignore_permissions=True)

        new_container_seal = frappe.new_doc("Container Seals")
        new_container_seal.update(
            {
                "reference_container_entry": doc.doctype,
                "creation_document_no": doc.name,
                "booking_number": doc.booking_number,
                "shipping_line": doc.shipping_line,
                "seal_number": value.seal_number,
                "collection_date": doc.collection_date,
                "parenttype": "Export",
                "parent": doc.export_reference,
                "parentfield": "container_information",
            }
        )
        new_container_seal.insert(ignore_permissions=True)
