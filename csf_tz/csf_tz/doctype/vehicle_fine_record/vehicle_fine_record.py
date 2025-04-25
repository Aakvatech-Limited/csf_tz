# -*- coding: utf-8 -*-
# Copyright (c) 2020, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe import _
import requests
from requests.exceptions import Timeout
from bs4 import BeautifulSoup
from csf_tz.custom_api import print_out
import re
import json
from time import sleep


class VehicleFineRecord(Document):
    def validate(self):
        """
        Validate the vehicle number plate and get the vehicle name

        1. Check if the vehicle number plate is valid
        2. Get the vehicle name from the vehicle number plate
        3. If the vehicle name is not found, set the vehicle name as the vehicle number plate
        """
        try:
            if self.vehicle:
                vehicle_name = frappe.get_value(
                    "Vehicle", {"number_plate": self.vehicle}, "name"
                )
                if vehicle_name:
                    self.vehicle_doc = vehicle_name
                else:
                    self.vehicle_doc = self.vehicle
        except Exception as e:
            frappe.log_error(
                title=f"Error in VehicleFineRecord.validate",
                message=frappe.get_traceback(),
            )


def check_fine_all_vehicles(batch_size=20):
    plate_list = frappe.get_all(
        "Vehicle", fields=["name", "number_plate"], limit_page_length=0
    )
    all_fine_list = []
    total_vehicles = len(plate_list)

    for i in range(0, total_vehicles, batch_size):
        batch_vehicles = plate_list[i : i + batch_size]
        for vehicle in batch_vehicles:
            # Enqueue get_fine(number_plate=vehicle["number_plate"] or vehicle["name"])
            frappe.enqueue(
                "csf_tz.csf_tz.doctype.vehicle_fine_record.vehicle_fine_record.get_fine",
                number_plate=vehicle["number_plate"] or vehicle["name"],
            )

            fine_list = []
            # fine_list = get_fine(
            #     number_plate=vehicle["number_plate"] or vehicle["name"]
            # )
            if fine_list and len(fine_list) > 0:
                all_fine_list.extend(fine_list)
            sleep(2)  # Sleep to avoid hitting the server too frequently

    # Get all the references that are not paid
    reference_list = frappe.get_all(
        "Vehicle Fine Record",
        filters={"status": ["!=", "PAID"], "reference": ["not in", all_fine_list]},
    )

    for i in range(0, len(reference_list), batch_size):
        batch_references = reference_list[i : i + batch_size]
        for reference in batch_references:
            # Enqueue get_fine(reference=reference["name"])
            frappe.enqueue(
                "csf_tz.csf_tz.doctype.vehicle_fine_record.vehicle_fine_record.get_fine",
                reference=reference["vehicle"],
            )
            sleep(2)  # Sleep to avoid hitting the server too frequently


@frappe.whitelist()
def get_fine(number_plate=None, reference=None):
    if not number_plate and not reference:
        print_out(
            _("Please provide either number plate or reference"),
            alert=True,
            add_traceback=True,
            to_error_log=True,
        )
        return

    if number_plate and len(number_plate) < 7:
        print_out(
            f"Please provide a valid number plate for {number_plate}",
            alert=True,
            add_traceback=True,
            to_error_log=True,
        )
        return

    fine_list = []
    url = "https://tms.tpf.go.tz/api/OffenceCheck"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    payload = {"vehicle": number_plate or reference}

    try:
        sleep(2)  # Sleep to avoid hitting the server too frequently
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        frappe.log_error("HTTP error", str(e))
        frappe.throw(f"Error contacting traffic system: {str(e)}")

    try:
        result = response.json()
    except Exception as e:
        frappe.log_error("Invalid JSON", str(e))
        frappe.throw("Invalid response format from traffic system")

    data = result.get("pending_transactions", [])

    if data:
        print(f"Vehicle: {number_plate or reference} has no pending transactions")
        return fine_list
    else:
        if frappe.db.exists("Vehicle Fine Record", payload):
            doc = frappe.get_doc("Vehicle Fine Record", payload)
            doc.status = "PAID"
            doc.save()

    frappe.db.commit()
    return fine_list