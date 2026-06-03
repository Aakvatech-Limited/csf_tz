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
                ) or frappe.get_value("Vehicle", {"license_plate": self.vehicle}, "name")
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
        "Vehicle", fields=["name", "number_plate", "license_plate"], limit_page_length=0
    )
    total_vehicles = len(plate_list)

    # Enqueue get_fine calls in the background for each vehicle
    for vehicle in plate_list:
        frappe.enqueue(
            "csf_tz.csf_tz.doctype.vehicle_fine_record.vehicle_fine_record.get_fine",
            number_plate=vehicle["number_plate"] or vehicle["license_plate"] or vehicle["name"],
        )
        sleep(0.5)  # Minimal delay to queue jobs efficiently

    frappe.logger().info(f"Enqueued fine checks for {total_vehicles} vehicles")

    # Enqueue marking old records as PAID (will run after fine checks complete)
    frappe.enqueue(
        "csf_tz.csf_tz.doctype.vehicle_fine_record.vehicle_fine_record.mark_old_records_as_paid",
    )

    return {"message": f"Enqueued fine checks for {total_vehicles} vehicles"}


def mark_old_records_as_paid(batch_size=20):
    """
    Mark Vehicle Fine Records as PAID if they're no longer in the TPF system
    This function is called after all get_fine calls complete
    """
    try:
        # Get all PENDING/UNPAID records
        unpaid_records = frappe.get_all(
            "Vehicle Fine Record",
            filters={"status": ["!=", "PAID"]},
            fields=["name", "vehicle", "reference"],
            limit_page_length=0
        )

        marked_as_paid = 0
        for i, record in enumerate(unpaid_records):
            try:
                # Check if this fine still exists in TPF
                still_pending = get_fine(reference=record.get("reference"))
                
                # If not in pending list, mark as PAID
                if not still_pending or record.get("reference") not in still_pending:
                    frappe.db.set_value(
                        "Vehicle Fine Record",
                        record.get("name"),
                        "status",
                        "PAID"
                    )
                    marked_as_paid += 1
                
                if i % 5 == 0:
                    sleep(1)  # Small delay every 5 records
                    
            except Exception as e:
                frappe.log_error(
                    title=f"Error checking fine {record.get('reference')}",
                    message=frappe.get_traceback()
                )
                continue

        frappe.db.commit()
        frappe.logger().info(f"Marked {marked_as_paid} old records as PAID")

    except Exception as e:
        frappe.log_error(
            title="Error in mark_old_records_as_paid",
            message=frappe.get_traceback()
        )


@frappe.whitelist()
def get_fine(number_plate=None, reference=None):
    if not number_plate and not reference:
        return []

    # Log invalid plates as warning (not error) - once per vehicle
    if number_plate and len(number_plate) < 7:
        frappe.logger().warning(f"Invalid number plate (too short): {number_plate}")
        return []

    fine_list = []
    url = "https://tms.tpf.go.tz/api/OffenceCheck"
    
    # Headers required by TPF API
    headers = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Origin": "https://tms.tpf.go.tz",
        "Referer": "https://tms.tpf.go.tz/",
        "Connection": "keep-alive",
    }

    payload = {"vehicle": number_plate or reference}

    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            sleep(retry_delay)
            response = requests.post(url, json=payload, headers=headers, timeout=30)  # Increased timeout
            response.raise_for_status()
            break  # Success, exit retry loop
            
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            # Retry transient network errors
            if attempt < max_retries - 1:
                retry_delay = 5 * (attempt + 1)  # 5s, 10s, 15s
                continue
            else:
                frappe.logger().warning(f"Connection timeout for {number_plate or reference} after {max_retries} retries")
                return []
                
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:  # Too Many Requests - retry
                if attempt < max_retries - 1:
                    retry_delay = 10 * (attempt + 1)
                    continue
                else:
                    frappe.logger().warning(f"Rate limit for {number_plate or reference} after {max_retries} retries")
                    return []
            elif response.status_code >= 500:  # 5xx Server errors - retry
                if attempt < max_retries - 1:
                    retry_delay = 10 * (attempt + 1)
                    continue
                else:
                    frappe.logger().warning(f"Server error for {number_plate or reference} after {max_retries} retries")
                    return []
            else:  # 4xx errors - don't retry
                frappe.log_error(title="TPF API Error", message=f"HTTP {response.status_code}: {str(e)}")
                return []
                
        except requests.exceptions.RequestException as e:
            frappe.log_error(title="TPF API Error", message=str(e))
            return []

    try:
        result = response.json()
    except Exception as e:
        frappe.log_error("Invalid JSON", str(e))
        frappe.throw("Invalid response format from traffic system")

    data = result.get("pending_transactions", [])
    vehicle_key = number_plate or reference

    if data:
        fine_list = [fine.get("reference") for fine in data if fine.get("reference")]
        if not fine_list:
            return fine_list

        filters = {"vehicle": vehicle_key, "status": ["!=", "PAID"], "reference": ["not in", fine_list]}
        
        # Get existing fine references to check for duplicates
        existing_refs = frappe.get_all(
            "Vehicle Fine Record",
            filters={"vehicle": vehicle_key, "reference": ["in", fine_list]},
            pluck="reference"
        )

        # Mark existing records NOT in current list as PAID
        for record in frappe.get_all("Vehicle Fine Record", filters=filters, pluck="name"):
            frappe.db.set_value("Vehicle Fine Record", record, "status", "PAID")

        # Create NEW Vehicle Fine Records for pending fines that don't exist
        for fine in data:
            fine_ref = fine.get("reference")
            if fine_ref and fine_ref not in existing_refs:
                try:
                    new_record = frappe.get_doc({
                        "doctype": "Vehicle Fine Record",
                        "vehicle": vehicle_key,
                        "reference": fine_ref,
                        "status": "PENDING",
                        "amount": fine.get("amount"),
                        "offence": fine.get("offence"),
                        "fine_date": fine.get("date"),
                    })
                    new_record.insert(ignore_permissions=True)
                except frappe.exceptions.DuplicateEntryError:
                    pass  # Record already exists, continue
                except Exception as e:
                    frappe.log_error(
                        title=f"Error creating fine record for {vehicle_key}",
                        message=frappe.get_traceback()
                    )
    else:
        filters = {"vehicle": vehicle_key, "status": ["!=", "PAID"]}

        for record in frappe.get_all("Vehicle Fine Record", filters=filters, pluck="name"):
            frappe.db.set_value("Vehicle Fine Record", record, "status", "PAID")

    frappe.db.commit()
    return fine_list