# Copyright (c) 2026, Aakvatech and contributors
# For license information, please see license.txt


import time
from time import sleep

import frappe
import requests
from frappe.model.document import Document
from frappe.utils import cint, getdate, now_datetime, nowdate

from csf_tz.csf_tz.doctype.vehicle_fine_record.vehicle_fine_record import (
	is_valid_number_plate,
	normalize_number_plate,
)
from csf_tz.vehicle_authority import (
	get_unique_vehicle_plates,
	is_authority_notification_event_enabled,
	send_authority_notification,
)

LATRA_GQL_URL = "https://rrims.latra.go.tz:8086/graphql"
LATRA_LOGIN_URL = "https://rrims.latra.go.tz:8086/user/login"
LATRA_BASIC_AUTH = "Basic bGFsaXM6MTIzNDU2Nzg="
TOKEN_EXPIRED = "TOKEN_EXPIRED"
RUN_TIME_BUDGET_SECONDS = 240
LATRA_TIMEOUT_SECONDS = 15
LATRA_MAX_RETRIES = 1

GQL_QUERY = """
query findMyCurrentLicensesPageable($pageableParam: PageableParamInput){
  findMyCurrentLicensesPageable(pageableParam: $pageableParam){
    content{
      licenseNumber
      licenseStatus
      validFrom
      validTo
      serviceType {
        name
        licenseType { licenseTypeName }
      }
      licenseInfoDetail {
        currentLicenseApplication {
          branch { name district { districtName } }
        }
      }
      vehicle{ vehicleRegistrationNumber }
    }
  }
}
"""

OFFENCE_GQL_QUERY = """
query allMyClientOffencesPageable($pageableParam: PageableParamInput) {
  allMyClientOffencesPageable(pageableParam: $pageableParam) {
    content {
      uid
      vehicleRegistrationNumber
      offenceReferenceNumber
      offenderName
      offenceDate
      paymentStatus
      amount
      clientOffenceType
      warningDescription
      comment
      offence { uid name code compoundedAmount }
      offenceLocation { uid name }
    }
    totalElements
  }
}
"""


class LatraLicenses(Document):
	pass


@frappe.whitelist()
def update_latra_records(force=0):
	token = _get_token() or _refresh_token()

	if not token:
		return {
			"message": "LATRA license sync skipped because no token is available.",
		}

	license_result = sync_all_latra_licenses(token)
	if license_result == TOKEN_EXPIRED:
		token = _refresh_token(token)
		if not token:
			return {
				"message": "LATRA license sync stopped because token refresh failed.",
			}
		license_result = sync_all_latra_licenses(token)

	if license_result == TOKEN_EXPIRED:
		return {
			"message": "LATRA license sync stopped due to auth failure.",
		}

	if license_result == "RATE_LIMITED":
		return {
			"message": "LATRA license sync stopped due to upstream throttling.",
		}

	frappe.db.commit()
	return {
		"licenses": license_result,
	}


@frappe.whitelist()
def update_latra_offences(force=0):
	plates = get_unique_vehicle_plates(
		normalize_number_plate=normalize_number_plate,
		is_valid_number_plate=is_valid_number_plate,
	)
	processed = saved = skipped = matched = 0

	if not plates:
		frappe.db.commit()
		return {
			"message": "Processed LATRA offence updates for 0 vehicle(s)",
			"processed": 0,
			"saved": 0,
			"skipped": 0,
			"completed_cycle": True,
		}

	token = _get_token()
	if not token:
		token = _refresh_token()
		if not token:
			frappe.log_error(title="LATRA: No Token", message="Set access_token in Latra Settings.")
			return {"message": "LATRA offence sync skipped because no token is available."}

	data = _fetch_all_offences(token)
	if data == TOKEN_EXPIRED:
		token = _refresh_token(token)
		data = _fetch_all_offences(token) if token else None
	if data == "RATE_LIMITED":
		return {"message": "LATRA offence sync stopped due to upstream throttling."}
	if not data:
		frappe.log_error(title="LATRA: Offence GraphQL Failed", message="Could not fetch LATRA offences.")
		return {"message": "LATRA offence sync stopped due to upstream failure."}

	rows_by_plate = {}
	for row in data:
		plate = normalize_number_plate(row.get("vehicleRegistrationNumber"))
		if not plate:
			continue
		rows_by_plate.setdefault(plate, []).append(row)

	for plate in plates:
		plate_rows = rows_by_plate.get(plate, [])
		if plate_rows:
			matched += 1

		for row in plate_rows:
			offence = row.get("offence") or {}
			location = row.get("offenceLocation") or {}
			values = {
				"mv_reg_number": plate,
				"offender_name": row.get("offenderName") or "",
				"offence_type": row.get("clientOffenceType") or "",
				"status": row.get("paymentStatus") or "",
				"offence": offence.get("name") or row.get("warningDescription") or "",
				"offence_date": _parse_date(row.get("offenceDate")),
				"location": location.get("name") or "",
				"reference_number": row.get("offenceReferenceNumber") or row.get("uid") or "",
				"amount": row.get("amount") or offence.get("compoundedAmount") or 0,
			}
			existing = frappe.db.get_value(
				"Latra Offence",
				{
					"mv_reg_number": values["mv_reg_number"],
					"reference_number": values["reference_number"],
					"offence_date": values["offence_date"],
					"offence": values["offence"],
				},
				["name", "status", "authority_notified_on_new", "authority_last_notified_status"],
				as_dict=True,
			)
			if existing:
				old_status = existing.status
				frappe.db.set_value("Latra Offence", existing.name, values)
				_notify_latra_offence(existing.name, values, is_new=False, old_status=old_status)
			else:
				doc = frappe.get_doc({"doctype": "Latra Offence", **values})
				doc.insert(ignore_permissions=True)
				_notify_latra_offence(doc.name, values, is_new=True)
			saved += 1

		if plate not in rows_by_plate:
			skipped += 1

		processed += 1

	frappe.db.commit()
	return {
		"message": (
			f"LATRA returned {len(data)} offence record(s); "
			f"matched {matched} local vehicle plate(s); "
			f"processed {processed} vehicle(s)"
		),
		"processed": processed,
		"saved": saved,
		"skipped": skipped,
		"matched": matched,
		"fetched_offences": len(data),
		"total_vehicles": len(plates),
		"completed_cycle": True,
	}


def send_pending_latra_offence_notifications():
	for row in frappe.get_all(
		"Latra Offence",
		fields=[
			"name",
			"mv_reg_number",
			"reference_number",
			"amount",
			"status",
			"authority_notified_on_new",
			"authority_last_notified_status",
		],
		limit_page_length=0,
	):
		values = {
			"mv_reg_number": row.mv_reg_number,
			"reference_number": row.reference_number,
			"amount": row.amount,
			"status": row.status,
		}

		if not row.authority_notified_on_new:
			_notify_latra_offence(row.name, values, is_new=True)

		last_status = row.authority_last_notified_status or ""
		current_status = row.status or ""
		if last_status and current_status and last_status != current_status:
			_notify_latra_offence(row.name, values, is_new=False, old_status=last_status)

	frappe.db.commit()


def sync_all_latra_licenses(token):
	plates = get_unique_vehicle_plates(
		normalize_number_plate=normalize_number_plate,
		is_valid_number_plate=is_valid_number_plate,
	)
	started_at = time.monotonic()
	all_licenses = _fetch_all_licenses(token)

	if all_licenses in (TOKEN_EXPIRED, "RATE_LIMITED", None):
		return all_licenses

	licenses_by_plate = {}
	for lic in all_licenses:
		vehicle_reg = normalize_number_plate((lic.get("vehicle") or {}).get("vehicleRegistrationNumber"))
		if not vehicle_reg:
			continue
		licenses_by_plate.setdefault(vehicle_reg, []).append(lic)

	processed = saved = skipped = matched = 0
	for plate in plates:
		if processed and (time.monotonic() - started_at) >= RUN_TIME_BUDGET_SECONDS:
			break

		matching_licenses = licenses_by_plate.get(plate, [])
		if not matching_licenses:
			skipped += 1
			processed += 1
			continue

		matching_licenses.sort(key=lambda d: str(d.get("validTo") or ""), reverse=True)
		matched += 1
		saved += _upsert_latra_license(plate, matching_licenses[0])
		frappe.db.commit()
		processed += 1

	return {
		"message": (
			f"LATRA returned {len(all_licenses)} license record(s); "
			f"matched {matched} local vehicle plate(s); "
			f"processed {processed} vehicle(s)"
		),
		"processed": processed,
		"saved": saved,
		"skipped": skipped,
		"matched": matched,
		"fetched_licenses": len(all_licenses),
		"total_vehicles": len(plates),
		"completed_cycle": processed >= len(plates),
	}


def _upsert_latra_license(plate_number, lic):
	try:
		license_number = lic.get("licenseNumber")
		if not license_number:
			frappe.logger().warning(f"[LATRA] No license number for {plate_number}")
			return 0

		values = {
			"vehicle": plate_number,
			"license_number": license_number,
			"license_status": lic.get("licenseStatus") or "",
			"license_type": _get_license_type(lic),
			"service_type": (lic.get("serviceType") or {}).get("name") or "",
			"place_issued": _get_place_issued(lic),
			"issue_date": _parse_date(lic.get("validFrom")),
			"expire_date": _parse_date(lic.get("validTo")),
		}

		if frappe.db.exists("Latra Licenses", license_number):
			frappe.db.set_value("Latra Licenses", license_number, values)
		else:
			frappe.get_doc({"doctype": "Latra Licenses", **values}).insert(ignore_permissions=True)
		return 1

	except frappe.exceptions.DuplicateEntryError:
		frappe.logger().warning(f"[LATRA] Duplicate entry for {lic.get('licenseNumber')}")
		return 0
	except Exception:
		frappe.log_error(
			title=f"LATRA: Error saving license for {plate_number}",
			message=frappe.get_traceback(),
		)
		return 0


def notify_latra_license_expiry():
	before_days = cint(frappe.db.get_single_value("CSF TZ Settings", "latra_license_notify_before_days") or 0)
	today = getdate(nowdate())

	for row in frappe.get_all(
		"Latra Licenses",
		fields=[
			"name",
			"vehicle",
			"license_number",
			"license_status",
			"expire_date",
			"authority_last_expiry_notification_key",
		],
		limit_page_length=0,
	):
		if not row.expire_date:
			continue

		expiry_date = getdate(row.expire_date)
		days_left = (expiry_date - today).days

		if days_left < 0:
			state_key = f"expired:{expiry_date}"
			subject = f"LATRA License Expired for Vehicle {row.vehicle or row.license_number}"
			message = (
				f"LATRA license {row.license_number} for vehicle {row.vehicle or '-'} "
				f"expired on {expiry_date}. Please renew and update the record."
			)
		elif before_days >= 0 and days_left <= before_days:
			state_key = f"pre-expiry:{expiry_date}"
			subject = f"LATRA License Expiry Reminder for Vehicle {row.vehicle or row.license_number}"
			message = (
				f"LATRA license {row.license_number} for vehicle {row.vehicle or '-'} "
				f"will expire on {expiry_date} ({days_left} day(s) left). "
				"Please renew before the expiry date."
			)
		else:
			continue

		if row.authority_last_expiry_notification_key == state_key:
			continue

		result = send_authority_notification("LATRA License", subject, message)
		if result.get("sent"):
			frappe.db.set_value(
				"Latra Licenses",
				row.name,
				{
					"authority_last_expiry_notification_key": state_key,
					"authority_last_expiry_notification_on": now_datetime(),
				},
				update_modified=False,
			)


def _notify_latra_offence(docname, values, is_new=False, old_status=None):
	current_status = values.get("status") or ""

	if is_new:
		if not is_authority_notification_event_enabled("LATRA Offence", "new"):
			return
		subject = f"LATRA Offence Alert: {values.get('mv_reg_number')}"
		message = (
			f"Vehicle {values.get('mv_reg_number') or '-'} has a new LATRA offence "
			f"({values.get('reference_number') or '-'}) with status {current_status} "
			f"and amount {values.get('amount') or 0}."
		)
		result = send_authority_notification("LATRA Offence", subject, message)
		if result.get("sent"):
			frappe.db.set_value(
				"Latra Offence",
				docname,
				{
					"authority_notified_on_new": now_datetime(),
					"authority_last_notified_status": current_status,
				},
				update_modified=False,
			)
		return

	if old_status != current_status:
		if not is_authority_notification_event_enabled("LATRA Offence", "status_change"):
			return
		subject = f"LATRA Offence Status Changed: {values.get('mv_reg_number')}"
		message = (
			f"Vehicle {values.get('mv_reg_number') or '-'} LATRA offence "
			f"({values.get('reference_number') or '-'}) changed status "
			f"from {old_status or '-'} to {current_status or '-'}."
		)
		result = send_authority_notification("LATRA Offence", subject, message)
		if result.get("sent"):
			frappe.db.set_value(
				"Latra Offence",
				docname,
				"authority_last_notified_status",
				current_status,
				update_modified=False,
			)


def _log_sync_summary(license_result, offence_result):
	try:
		license_message = (
			license_result.get("message") if isinstance(license_result, dict) else str(license_result)
		)
		offence_message = (
			offence_result.get("message") if isinstance(offence_result, dict) else str(offence_result)
		)
		frappe.log_error(
			title="LATRA Sync Summary",
			message=f"Licenses: {license_message}\nOffences: {offence_message}",
		)
	except Exception:
		frappe.log_error(
			title="LATRA: Failed to write sync summary",
			message=frappe.get_traceback(),
		)


def _get_token():
	try:
		cached_token = frappe.cache().get_value(_token_cache_key(), expires=True)
		if cached_token:
			return str(cached_token).strip()

		token = (frappe.db.get_single_value("Latra Settings", "access_token") or "").strip()
		if token:
			frappe.cache().set_value(_token_cache_key(), token, expires_in_sec=60 * 60 * 8)
			frappe.logger().debug("[LATRA] Using existing token")
		else:
			frappe.logger().warning("[LATRA] No token found in settings")
		return token
	except Exception as e:
		frappe.log_error(
			title="LATRA: Error reading token",
			message=str(e),
		)
		return None


def _refresh_token(old_token=None):
	"""
	Log in to the LATRA API using stored credentials and save the new token.
	Returns the new token string, or None on failure.
	"""
	lock = frappe.cache().lock(
		f"{frappe.local.site}:latra_token_refresh",
		timeout=120,
		blocking_timeout=60,
	)
	with lock:
		current_token = _get_token()
		if old_token and current_token and current_token != old_token:
			return current_token
		return _refresh_token_locked()


def _refresh_token_locked():
	try:
		settings = frappe.get_single("Latra Settings")
		email = (settings.get("username") or "").strip()
		try:
			password = (settings.get_password("password") or "").strip()
		except Exception:
			password = (settings.get("password") or "").strip()
	except Exception:
		frappe.log_error(
			title="LATRA: Settings missing",
			message=frappe.get_traceback(),
		)
		return None

	if not email or not password:
		frappe.log_error(
			title="LATRA: Credentials missing",
			message="Username or password not set in Latra Settings",
		)
		return None

	try:
		frappe.logger().info("[LATRA] Attempting token refresh...")
		response = requests.post(
			LATRA_LOGIN_URL,
			data={"username": email, "password": password},
			headers={
				"Authorization": LATRA_BASIC_AUTH,
				"Content-Type": "application/x-www-form-urlencoded",
				"Accept": "application/json",
			},
			timeout=30,
		)
		if response.status_code >= 400:
			frappe.log_error(
				title="LATRA: Token refresh HTTP failed",
				message=f"HTTP {response.status_code}: {response.text[:1000]}",
			)
			return None
		ld = response.json() if response.text else {}
		d = ld.get("data") if isinstance(ld.get("data"), dict) else {}
		new_token = (
			ld.get("token")
			or ld.get("accessToken")
			or ld.get("access_token")
			or d.get("token")
			or d.get("accessToken")
			or d.get("access_token")
			or ""
		).strip()
	except Exception:
		frappe.log_error(
			title="LATRA: Token refresh failed",
			message=frappe.get_traceback(),
		)
		return None

	if new_token:
		frappe.db.set_single_value("Latra Settings", "access_token", new_token)
		frappe.cache().set_value(_token_cache_key(), new_token, expires_in_sec=60 * 60 * 8)
		frappe.logger().info("[LATRA] Token refreshed successfully")
	else:
		frappe.log_error(
			title="LATRA: No token in login response",
			message=f"Response: {ld}",
		)

	return new_token or None


def _token_cache_key():
	return f"{frappe.local.site}:latra_access_token"


def _fetch_all_offences(token):
	page_size = 500
	page_index = 0
	all_rows = []

	while True:
		result = _call_offences_graphql_page(token, first=page_index, size=page_size)
		if result in (TOKEN_EXPIRED, "RATE_LIMITED", None):
			return result

		page = result.get("allMyClientOffencesPageable") or {}
		content = page.get("content") or []
		total_elements = cint(page.get("totalElements") or 0)

		if not content:
			break

		all_rows.extend(content)
		if len(content) < page_size:
			break

		page_index += 1

		if total_elements and len(all_rows) >= total_elements:
			break

	if total_elements and total_elements > page_size:
		frappe.logger().info(f"[LATRA] Fetched {len(all_rows)} offences across paginated results")

	return all_rows


def _call_offences_graphql_page(token, first=0, size=500):
	payload = {
		"operationName": "allMyClientOffencesPageable",
		"variables": {
			"pageableParam": {
				"first": first,
				"size": size,
				"sortBy": "id",
				"sortDirection": "DESC",
				"searchFields": [],
			}
		},
		"query": OFFENCE_GQL_QUERY,
	}
	response = None

	for attempt in range(LATRA_MAX_RETRIES):
		try:
			if attempt > 0:
				sleep(5 * attempt)

			response = requests.post(
				LATRA_GQL_URL,
				json=payload,
				headers={
					"Authorization": f"Bearer {token}",
					"Accept": "application/json",
					"Content-Type": "application/json",
				},
				timeout=LATRA_TIMEOUT_SECONDS,
			)
			if response.status_code == 401:
				return TOKEN_EXPIRED
			if response.status_code == 429:
				return "RATE_LIMITED"
			response.raise_for_status()
			break

		except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
			if attempt < LATRA_MAX_RETRIES - 1:
				continue
			frappe.log_error(
				title="LATRA Offence Connection Error",
				message=f"Page {first} size {size}: {str(e)}",
			)
			return None

		except requests.exceptions.HTTPError:
			status = response.status_code if response is not None else 0
			if status in (408,) or status >= 500:
				if attempt < LATRA_MAX_RETRIES - 1:
					continue
				frappe.log_error(
					title="LATRA Offence HTTP Error",
					message=f"HTTP {status} on page {first}: {response.text[:500] if response else ''}",
				)
				return None
			frappe.log_error(
				title="LATRA Offence API Error",
				message=f"HTTP {status} on page {first}: {response.text[:500] if response else ''}",
			)
			return None

		except requests.exceptions.RequestException as e:
			frappe.log_error(
				title="LATRA Offence Request Error",
				message=str(e),
			)
			return None

	if response is None:
		return None

	try:
		result = response.json()
		if result.get("errors"):
			frappe.log_error(
				title="LATRA Offence GraphQL Error",
				message=frappe.as_json(result.get("errors"))[:2000],
			)
			return None
		return result.get("data")
	except Exception:
		frappe.log_error(
			title="LATRA Offence Invalid JSON",
			message=f"Non-JSON response on page {first}: {response.text[:500] if response else 'No response'}",
		)
		return None


def _fetch_all_licenses(token):
	page_size = 200
	page_index = 0
	all_licenses = []

	while True:
		result = _call_license_page(token, first=page_index, size=page_size)
		if result in (TOKEN_EXPIRED, "RATE_LIMITED", None):
			return result

		content = (result.get("findMyCurrentLicensesPageable") or {}).get("content") or []
		if not content:
			break

		all_licenses.extend(content)
		if len(content) < page_size:
			break

		page_index += 1

	return all_licenses


def _call_license_page(token, first=0, size=200):
	payload = {
		"operationName": "findMyCurrentLicensesPageable",
		"variables": {
			"pageableParam": {
				"first": first,
				"size": size,
				"sortBy": "id",
				"sortDirection": "DESC",
				"searchFields": [],
			}
		},
		"query": GQL_QUERY,
	}
	headers = {
		"Authorization": f"Bearer {token}",
		"Accept": "application/json",
		"Content-Type": "application/json",
	}

	max_retries = LATRA_MAX_RETRIES
	timeout = LATRA_TIMEOUT_SECONDS
	response = None

	for attempt in range(max_retries):
		try:
			if attempt > 0:
				sleep(5 * attempt)

			response = requests.post(LATRA_GQL_URL, json=payload, headers=headers, timeout=timeout)

			if response.status_code == 401:
				return TOKEN_EXPIRED
			if response.status_code == 429:
				return "RATE_LIMITED"

			response.raise_for_status()
			break

		except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
			if attempt < max_retries - 1:
				continue
			return None

		except requests.exceptions.HTTPError:
			status = response.status_code if response is not None else 0
			if status in (408,) or status >= 500:
				if attempt < max_retries - 1:
					continue
				return None
			frappe.log_error(
				title="LATRA API Error",
				message=f"HTTP {status}: {response.text[:500] if response else ''}",
			)
			return None

		except requests.exceptions.RequestException as e:
			frappe.log_error(title="LATRA API Error", message=str(e))
			return None

	if response is None:
		return None

	try:
		result = response.json()
		errors = result.get("errors")
		if errors:
			frappe.log_error(
				title="LATRA GraphQL Error",
				message=frappe.as_json(errors)[:2000],
			)
			return None
		return result.get("data")
	except Exception:
		frappe.log_error(
			title="LATRA API: Invalid JSON",
			message=f"Non-JSON response: {response.text[:500] if response else 'No response'}",
		)
		return None


def _parse_date(value):
	if not value:
		return None
	try:
		return str(value)[:10] if "T" in str(value) else str(value)
	except Exception:
		return None


def _get_place_issued(license_row):
	branch = ((license_row.get("licenseInfoDetail") or {}).get("currentLicenseApplication") or {}).get(
		"branch"
	) or {}
	district = branch.get("district") or {}
	branch_name = branch.get("name") or ""
	district_name = district.get("districtName") or ""
	return f"{branch_name} ({district_name})" if branch_name and district_name else branch_name


def _get_license_type(license_row):
	license_type = (
		((license_row.get("serviceType") or {}).get("licenseType") or {}).get("licenseTypeName")
	) or ""
	return {
		"GOODSCARRYINGVEHICLE": "GCV",
		"PUBLICSERVICEVEHICLE": "PSV",
		"PRIVATEHIRE": "Private Hire",
	}.get(license_type, license_type)
