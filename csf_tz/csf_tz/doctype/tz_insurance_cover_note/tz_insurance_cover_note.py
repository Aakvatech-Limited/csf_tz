# Copyright (c) 2022, Aakvatech and contributors
# For license information, please see license.txt

import json
from datetime import datetime
from time import sleep

import frappe
import requests
from frappe.model.document import Document
from frappe.utils import cint, getdate, now_datetime, nowdate

from csf_tz.csf_tz.doctype.vehicle_fine_record.vehicle_fine_record import (
	is_valid_number_plate,
	normalize_number_plate,
)
from csf_tz.vehicle_authority import get_vehicle_like_records, send_authority_notification


class TZInsuranceCoverNote(Document):
	pass


@frappe.whitelist()
def update_covernote_docs():
	"""Create or Update covernote document after getting necessary details from tira

	The routine to create or update covernote document runs on 00:00 am, 1st date of every month
	Forexample:
		for June: a routine will run on 00:00 am, June 1, 2022
	"""
	seen_plates = set()
	processed = 0

	for vehicle in get_vehicle_like_records():
		plate = normalize_number_plate(vehicle.plate_number)
		if not plate or not is_valid_number_plate(plate):
			continue
		if plate in seen_plates:
			continue
		seen_plates.add(plate)
		fetch_and_update_covernote(plate)
		processed += 1

	frappe.logger().info(f"[CoverNote] Processed covernote updates for {processed} vehicles")
	return {"message": f"Processed covernote updates for {processed} vehicles"}


def fetch_and_update_covernote(plate_number):
	"""
	Fetch and update covernote for a specific vehicle plate.
	"""
	req = get_covernote_details(plate_number)
	try:
		if not req or not req.get("data"):
			return

		for record in req.get("data"):
			if not frappe.db.exists("TZ Insurance Cover Note", record["coverNoteNumber"]):
				doc = frappe.new_doc("TZ Insurance Cover Note")
			else:
				doc = frappe.get_doc("TZ Insurance Cover Note", record["coverNoteNumber"])

			for key, value in record.items():
				if key.lower() == "motor":
					row = {}
					doc.insurance_motors = []
					for motor_child_key, motor_child_value in value.items():
						motor_new_value = None
						if motor_child_value and motor_child_key.lower() in ["createddate", "updateddate"]:
							unix_timestamp_int = cint(motor_child_value)
							motor_new_value = datetime.utcfromtimestamp(unix_timestamp_int / 1000).strftime(
								"%Y-%m-%d %H:%M:%S"
							)
						else:
							motor_new_value = motor_child_value

						row[motor_child_key.lower()] = motor_new_value

					doc.append("insurance_motors", row)

				if key.lower() == "company":
					row = {}
					doc.insurance_provider = []
					for company_child_key, company_child_value in value.items():
						company_new_value = None
						if company_child_value and company_child_key.lower() in [
							"createddate",
							"updateddate",
							"incorporationdate",
							"initialregistrationdate",
							"businesscommencementdate",
						]:
							unix_timestamp_int = cint(company_child_value)
							company_new_value = datetime.utcfromtimestamp(unix_timestamp_int / 1000).strftime(
								"%Y-%m-%d %H:%M:%S"
							)

						elif company_child_key.lower() == "shareholders":
							company_new_value = json.dumps(company_child_value)

						else:
							company_new_value = company_child_value

						row[company_child_key.lower()] = company_new_value

					doc.append("insurance_provider", row)

				if key.lower() == "policyholders":
					doc.policy_holders = []
					for _i, row in enumerate(value):
						new_row = {}
						for policy_child_key, policy_child_value in row.items():
							policy_new_value = None
							if policy_child_value and policy_child_key.lower() in [
								"createddate",
								"updateddate",
								"policyholderbirthdate",
							]:
								unix_timestamp_int = cint(policy_child_value)
								policy_new_value = datetime.utcfromtimestamp(
									unix_timestamp_int / 1000
								).strftime("%Y-%m-%d %H:%M:%S")

							else:
								policy_new_value = policy_child_value

							new_row[policy_child_key.lower()] = policy_new_value

						doc.append("policy_holders", new_row)

				if key.lower() not in [
					"covernotestartdate",
					"covernoteenddate",
					"company",
					"motor",
					"policyholders",
				]:
					doc.update({key.lower(): value})

				if key.lower() in ["covernotestartdate", "covernoteenddate"]:
					unix_timestamp_int = cint(value)
					date_value = datetime.utcfromtimestamp(unix_timestamp_int / 1000.0).strftime(
						"%Y-%m-%d %H:%M:%S"
					)
					doc.update({key.lower(): date_value})

			doc.vehicle = plate_number
			doc.save(ignore_permissions=True)

		frappe.db.commit()

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), str(e))


def notify_tira_covernote_expiry():
	before_days = cint(frappe.db.get_single_value("CSF TZ Settings", "tira_notify_before_days") or 0)
	today = getdate(nowdate())

	for row in frappe.get_all(
		"TZ Insurance Cover Note",
		fields=[
			"name",
			"vehicle",
			"covernotenumber",
			"covernoteenddate",
			"authority_last_expiry_notification_key",
		],
		limit_page_length=0,
	):
		if not row.covernoteenddate:
			continue

		expiry_date = getdate(str(row.covernoteenddate)[:10])
		days_left = (expiry_date - today).days

		if days_left < 0:
			state_key = f"expired:{expiry_date}"
			subject = f"TIRA Cover Note Expired for Vehicle {row.vehicle or row.covernotenumber}"
			message = (
				f"TIRA cover note {row.covernotenumber} for vehicle {row.vehicle or '-'} "
				f"expired on {expiry_date}. Please renew and update the record."
			)
		elif before_days >= 0 and days_left <= before_days:
			state_key = f"pre-expiry:{expiry_date}"
			subject = f"TIRA Cover Note Expiry Reminder for Vehicle {row.vehicle or row.covernotenumber}"
			message = (
				f"TIRA cover note {row.covernotenumber} for vehicle {row.vehicle or '-'} "
				f"will expire on {expiry_date} ({days_left} day(s) left). "
				"Please renew before the expiry date."
			)
		else:
			continue

		if row.authority_last_expiry_notification_key == state_key:
			continue

		result = send_authority_notification("TIRA", subject, message)
		if result.get("sent"):
			frappe.db.set_value(
				"TZ Insurance Cover Note",
				row.name,
				{
					"authority_last_expiry_notification_key": state_key,
					"authority_last_expiry_notification_on": now_datetime(),
				},
				update_modified=False,
			)

	frappe.db.commit()


def get_covernote_details(regnumber):
	"""Fetch motor insurance details from tira

	:param regnumber: car registration number
	"""
	url = "https://tiramis.tira.go.tz/covernote/api/public/portal/verify"

	payload = json.dumps({"paramType": 2, "searchParam": regnumber})
	headers = {"Accept": "application/json", "Content-Type": "application/json"}

	max_retries = 3
	response = None

	for attempt in range(max_retries):
		try:
			if attempt > 0:
				sleep(5 * attempt)

			response = requests.post(url, headers=headers, data=payload, timeout=30, verify=False)
			response.raise_for_status()
			break

		except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
			if attempt < max_retries - 1:
				continue
			frappe.logger().warning(
				f"[CoverNote] Connection timeout for {regnumber} after {max_retries} retries"
			)
			return None

		except requests.exceptions.HTTPError:
			status = response.status_code if response is not None else 0
			if status in (408, 429) or status >= 500:
				if attempt < max_retries - 1:
					continue
				frappe.logger().warning(
					f"[CoverNote] HTTP {status} for {regnumber} after {max_retries} retries"
				)
				return None
			else:
				frappe.log_error(
					title="Tiramis API Error",
					message=f"HTTP {status} for {regnumber}: {response.text[:500] if response is not None else ''}",
				)
				return None

		except requests.exceptions.RequestException as e:
			frappe.log_error(title="Tiramis API Error", message=str(e))
			return None

	if response is None:
		return None

	try:
		if response.status_code == 200:
			return response.json()
		else:
			frappe.log_error(response.text, str(response.status_code))
			return None
	except Exception:
		frappe.log_error(
			title="Tiramis API: Invalid JSON",
			message=f"Non-JSON response for {regnumber}: {response.text[:500]}",
		)
		return None
