# -*- coding: utf-8 -*-
# Copyright (c) 2020, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe import _
import requests
from requests.exceptions import RequestException
import time
from csf_tz.custom_api import print_out

class VehicleFineRecord(Document):
    def validate(self):
        try:
            if self.vehicle:
                vehicle_name = frappe.get_value(
                    "Vehicle", {"number_plate": self.vehicle}, "name"
                )
                self.vehicle_doc = vehicle_name or self.vehicle
        except Exception as e:
            frappe.log_error(
                title="Error in VehicleFineRecord.validate",
                message=frappe.get_traceback(),
            )

@frappe.whitelist()
def check_fine_all_vehicles(batch_size=5):  # Reduced batch size further
    try:
        plate_list = frappe.get_all(
            "Vehicle", 
            fields=["name", "number_plate"], 
            filters={"vehicle_status": "RUNNING"},
            limit_page_length=0
        )
        
        total_vehicles = len(plate_list)
        frappe.logger().info(f"Starting to process {total_vehicles} vehicles")

        for i, vehicle in enumerate(plate_list):
            # Add delay between enqueuing jobs
            if i > 0 and i % batch_size == 0:
                time.sleep(5)  # 5 second delay every batch

            frappe.enqueue(
                "csf_tz.csf_tz.doctype.vehicle_fine_record.vehicle_fine_record.get_fine",
                number_plate=vehicle["number_plate"] or vehicle["name"],
                enqueue_after_commit=True,
                timeout=300,
                queue="long"  # Use a dedicated queue
            )

    except Exception as e:
        frappe.log_error(
            title="Error in check_fine_all_vehicles",
            message=frappe.get_traceback()
        )

@frappe.whitelist()
def get_fine(number_plate=None, reference=None):
    try:
        if not number_plate and not reference:
            return []

        if number_plate and len(number_plate) < 7:
            return []

        # Initial delay to prevent immediate rate limiting
        time.sleep(1)

        url = "https://tms.tpf.go.tz/api/OffenceCheck"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = {"vehicle": number_plate or reference}

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 10))
                frappe.logger().info(f"Rate limited. Waiting {retry_after} seconds")
                time.sleep(retry_after)
                response = requests.post(url, json=payload, headers=headers, timeout=15)
                
            response.raise_for_status()
            
        except RequestException as e:
            frappe.log_error(f"API Request failed for {payload['vehicle']}", str(e))
            return []

        try:
            result = response.json()
        except ValueError:
            return []

        data = result.get("pending_transactions", [])
        
        if not data:
            if frappe.db.exists("Vehicle Fine Record", payload):
                doc = frappe.get_doc("Vehicle Fine Record", payload)
                doc.status = "PAID"
                doc.save(ignore_permissions=True)
            return []

        # Process fines
        for fine in data:
            if not frappe.db.exists("Vehicle Fine Record", fine.get("reference")):
                doc = frappe.get_doc({
                    "doctype": "Vehicle Fine Record",
                    "vehicle": payload['vehicle'],
                    "reference": fine.get("reference"),
                    "offence": fine.get("offence"),
                    "amount": fine.get("amount"),
                    "status": fine.get("status"),
                    "date": fine.get("date")
                })
                doc.insert(ignore_permissions=True)

        frappe.db.commit()
        return [fine.get("reference") for fine in data]

    except Exception as e:
        frappe.log_error(
            title=f"Error processing {number_plate or reference}",
            message=frappe.get_traceback()
        )
        return []