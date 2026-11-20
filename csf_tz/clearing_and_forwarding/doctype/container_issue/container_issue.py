# -*- coding: utf-8 -*-
# Copyright (c) 2019, Bravo Logisitcs and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class ContainerIssue(Document):
    def on_submit(self):
        update_container(self)
        update_container_seal(self)


# update_container_seal_child(self);

# def on_cancel(self):
# remove_booking_container(self);


@frappe.whitelist()
def update_container(doc):
    docs = doc.container_detail
    for d in docs:
        update_container = frappe.get_doc("Container", d.container_no)
        update_container.booking_number = (doc.booking_number,)
        update_container.export_reference = (doc.export_reference,)
        update_container.seal_number = (
            frappe.db.get_value("Container Seals", d.seal_number, "seal_number"),
        )
        update_container.db_set("number_of_bundles", d.number_of_bundles)
        update_container.db_set("gross_weight", d.gross_weight)
        update_container.db_set("net_weight", d.net_weight)
        update_container.parenttype = ("Export",)
        update_container.parent = (doc.export_reference,)
        update_container.parentfield = "container_information"
        update_container.save()


@frappe.whitelist()
def update_container_seal(doc):
    seals = doc.container_detail

    for seal in seals:
        update_container_seal = frappe.get_doc("Container Seals", seal.seal_number)
        update_container_seal.export_reference = (doc.export_reference,)
        update_container_seal.booking_number = (doc.booking_number,)
        update_container_seal.parenttype = ("Export",)
        update_container_seal.parent = (doc.export_reference,)
        update_container_seal.parentfield = "container_information"
        update_container_seal.save()
