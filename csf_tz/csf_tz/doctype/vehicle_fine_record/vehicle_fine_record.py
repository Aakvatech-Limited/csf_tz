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
from frappe.utils import create_batch


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
    all_number_plates = [v["number_plate"] or v["name"] for v in plate_list]
    all_fine_list = []
    total_vehicles = len(all_number_plates)

    for i in range(0, total_vehicles, batch_size):
        batch_plates = all_number_plates[i : i + batch_size]
        fine_list = get_fine(number_plates=batch_plates, batch_size=batch_size)
        if fine_list and len(fine_list) > 0:
            all_fine_list.extend(fine_list)
        sleep(2)  # Sleep between batches only

    # Get all the references that are not paid
    reference_list = frappe.get_all(
        "Vehicle Fine Record",
        filters={"status": ["!=", "PAID"], "reference": ["not in", all_fine_list]},
    )
    all_references = [r["vehicle"] for r in reference_list]
    for i in range(0, len(all_references), batch_size):
        batch_refs = all_references[i : i + batch_size]
        get_fine(references=batch_refs, batch_size=batch_size)
        sleep(2)  # Sleep between batches


@frappe.whitelist()
def get_fine(number_plates=None, references=None, batch_size=20, max_retries=3, retry_delay=5):
    """
    Enhanced get_fine: Accepts a list of number plates or references and processes them in batches using create_batch.
    Args:
        number_plates (list): List of number plates.
        references (list): List of references.
        batch_size (int): Batch size for processing.
        max_retries (int): Max retries for 429 errors.
        retry_delay (int): Initial delay in seconds for retry.
    Returns:
        list: List of fine results.
    """
    if not number_plates and not references:
        print_out(
            _("Please provide either number plates or references (as lists)"),
            alert=True,
            add_traceback=True,
            to_error_log=True,
        )
        return []
    # Combine both lists if provided
    items = []
    if number_plates:
        items.extend(number_plates)
    if references:
        items.extend(references)
    results = []
    url = "https://tms.tpf.go.tz/api/OffenceCheck"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    for batch in create_batch(items, batch_size):
        for item in batch:
            payload = {"vehicle": item}
            retries = 0
            while retries <= max_retries:
                try:
                    sleep(2)
                    response = requests.post(url, json=payload, headers=headers, timeout=10)
                    response.raise_for_status()
                    try:
                        result = response.json()
                    except Exception as e:
                        frappe.log_error("Invalid JSON", str(e))
                        break
                    data = result.get("pending_transactions", [])
                    if data:
                        continue
                        # print(f"Vehicle: {item} has no pending transactions")
                    else:
                        if frappe.db.exists("Vehicle Fine Record", payload):
                            doc = frappe.get_doc("Vehicle Fine Record", payload)
                            doc.status = "PAID"
                            doc.save()
                    frappe.db.commit()
                    results.append(result)
                    break
                except requests.exceptions.HTTPError as e:
                    if hasattr(response, 'status_code') and response.status_code == 429:
                        sleep(retry_delay * (2 ** retries))
                        retries += 1
                        continue
                    else:
                        frappe.log_error("HTTP error", str(e))
                        break
                except Exception as e:
                    frappe.log_error("Request error", str(e))
                    break
            if retries > max_retries:
                frappe.log_error("Max retries exceeded for 429 error", str(payload))
    return results
