import frappe

AUTHORITY_REFERENCE_TYPES = (
	"LATRA License",
	"LATRA Offence",
	"TIRA",
	"Vehicle Fine",
)

AUTHORITY_ENABLE_FIELD_MAP = {
	"LATRA License": "enable_latra_license_notifications",
	"LATRA Offence": "enable_latra_offence_notifications",
	"TIRA": "enable_tira_notifications",
	"Vehicle Fine": "enable_vehicle_fine_notifications",
}

AUTHORITY_EVENT_ENABLE_FIELD_MAP = {
	("LATRA Offence", "new"): "latra_offence_notify_on_new",
	("LATRA Offence", "status_change"): "latra_offence_notify_on_status_change",
	("Vehicle Fine", "new"): "vehicle_fine_notify_on_new",
	("Vehicle Fine", "status_change"): "vehicle_fine_notify_on_status_change",
}


PLATE_FIELD_CANDIDATES = (
	"license_plate",
	"plate_number",
	"number_plate",
	"registration_number",
)


def get_vehicle_plate(doc_or_values, meta=None):
	"""Resolve a registration number from any vehicle-like document."""
	if meta is None and getattr(doc_or_values, "doctype", None):
		meta = doc_or_values.meta

	for fieldname in PLATE_FIELD_CANDIDATES:
		if fieldname != "name" and meta and not meta.has_field(fieldname):
			continue

		value = doc_or_values.get(fieldname) if fieldname != "name" else doc_or_values.get("name")
		if value and str(value).strip():
			return str(value).strip()


def has_vehicle_plate_field(meta):
	return any(meta.has_field(fieldname) for fieldname in PLATE_FIELD_CANDIDATES if fieldname != "name")


def get_vehicle_like_doctypes():
	for doctype in frappe.get_all(
		"DocType",
		filters={"istable": 0, "issingle": 0},
		pluck="name",
	):
		try:
			meta = frappe.get_meta(doctype)
		except Exception:
			continue

		if has_vehicle_plate_field(meta):
			yield doctype, meta


def get_vehicle_like_records():
	for doctype, meta in get_vehicle_like_doctypes():
		fields = ["name"]
		fields.extend(
			fieldname
			for fieldname in PLATE_FIELD_CANDIDATES
			if fieldname != "name" and meta.has_field(fieldname)
		)

		for row in frappe.get_all(doctype, fields=fields, limit_page_length=0):
			plate_number = get_vehicle_plate(row, meta=meta)
			if plate_number:
				yield frappe._dict(
					{
						"doctype": doctype,
						"name": row.name,
						"plate_number": plate_number,
					}
				)


def get_vehicle_docname_by_plate(plate_number):
	if not plate_number or not frappe.db.exists("DocType", "Vehicle"):
		return

	meta = frappe.get_meta("Vehicle")
	for fieldname in PLATE_FIELD_CANDIDATES:
		if meta.has_field(fieldname):
			vehicle_name = frappe.db.get_value("Vehicle", {fieldname: plate_number}, "name")
		else:
			vehicle_name = None

		if vehicle_name:
			return vehicle_name


def get_unique_vehicle_plates(normalize_number_plate=None, is_valid_number_plate=None):
	plates = {}

	for record in get_vehicle_like_records():
		plate = record.plate_number
		if normalize_number_plate:
			plate = normalize_number_plate(plate)

		if not plate:
			continue

		if is_valid_number_plate and not is_valid_number_plate(plate):
			continue

		if plate not in plates:
			plates[plate] = plate

	return sorted(plates)


def get_authority_notification_roles(reference_type):
	if reference_type not in AUTHORITY_REFERENCE_TYPES:
		return []

	try:
		settings = frappe.get_single("CSF TZ Settings")
	except Exception:
		return []

	return [
		row.role
		for row in (settings.get("authority_notification_roles") or [])
		if row.reference_type == reference_type and row.role
	]


def get_authority_notification_recipients(reference_type):
	recipients = {}

	for role in get_authority_notification_roles(reference_type):
		role_users = frappe.get_all(
			"Has Role",
			filters={"role": role, "parenttype": "User"},
			fields=["parent"],
			limit_page_length=0,
		)
		for row in role_users:
			user = frappe.db.get_value(
				"User",
				row.parent,
				["email", "enabled", "user_type"],
				as_dict=True,
			)
			if not user or not user.enabled or user.user_type == "Website User":
				continue
			email = (user.email or "").strip()
			if email:
				recipients[email] = email

	return sorted(recipients)


def is_authority_notification_enabled(reference_type):
	fieldname = AUTHORITY_ENABLE_FIELD_MAP.get(reference_type)
	if not fieldname:
		return False
	return bool(frappe.db.get_single_value("CSF TZ Settings", fieldname))


def is_authority_notification_event_enabled(reference_type, event_type):
	fieldname = AUTHORITY_EVENT_ENABLE_FIELD_MAP.get((reference_type, event_type))
	if not fieldname:
		return is_authority_notification_enabled(reference_type)
	return bool(frappe.db.get_single_value("CSF TZ Settings", fieldname))


def send_authority_notification(reference_type, subject, message, now=True):
	if not is_authority_notification_enabled(reference_type):
		return {"sent": False, "reason": "disabled"}

	recipients = get_authority_notification_recipients(reference_type)
	if not recipients:
		return {"sent": False, "reason": "no_recipients"}

	frappe.sendmail(
		recipients=recipients,
		subject=subject,
		message=message,
		now=now,
	)
	return {"sent": True, "reason": "sent", "recipients": recipients}


def run_daily_authority_notifications():
	from csf_tz.csf_tz.doctype.latra_licenses.latra_licenses import (
		notify_latra_license_expiry,
		send_pending_latra_offence_notifications,
	)
	from csf_tz.csf_tz.doctype.tz_insurance_cover_note.tz_insurance_cover_note import (
		notify_tira_covernote_expiry,
	)
	from csf_tz.csf_tz.doctype.vehicle_fine_record.vehicle_fine_record import (
		send_pending_vehicle_fine_notifications,
	)

	notify_latra_license_expiry()
	send_pending_latra_offence_notifications()
	notify_tira_covernote_expiry()
	send_pending_vehicle_fine_notifications()
