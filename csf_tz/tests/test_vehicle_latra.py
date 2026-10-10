from unittest.mock import patch

import frappe
import requests
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from csf_tz.csf_tz.doctype.latra_licenses import latra_licenses as module
from csf_tz.csf_tz.doctype.latra_licenses.latra_licenses import (
	TOKEN_EXPIRED,
	notify_latra_license_expiry,
	send_pending_latra_offence_notifications,
	sync_all_latra_licenses,
	update_latra_offences,
	update_latra_records,
)
from csf_tz.tests.integration_fixtures import FakeResponse
from csf_tz.tests.test_vehicle_authority import AUTHORITY_USER, configure_authority_notifications

PLATES = ["T444LLL", "T555LLL"]


class TestLatraHTTPMethods(IntegrationTestCase):
	def test_mutating_sync_endpoints_require_post(self):
		for endpoint in (update_latra_records, update_latra_offences):
			self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[endpoint], ["POST"])


def license_row(plate, number, valid_to, license_type="GOODSCARRYINGVEHICLE"):
	return {
		"licenseNumber": number,
		"licenseStatus": "ACTIVE",
		"validFrom": "2026-01-01T00:00:00",
		"validTo": valid_to,
		"serviceType": {"name": "Cargo", "licenseType": {"licenseTypeName": license_type}},
		"licenseInfoDetail": {
			"currentLicenseApplication": {"branch": {"name": "Dar", "district": {"districtName": "Ilala"}}}
		},
		"vehicle": {"vehicleRegistrationNumber": plate},
	}


def offence_row(plate, reference, status="UNPAID"):
	return {
		"uid": f"uid-{reference}",
		"vehicleRegistrationNumber": plate,
		"offenceReferenceNumber": reference,
		"offenderName": "Driver",
		"offenceDate": "2026-02-01T10:00:00",
		"paymentStatus": status,
		"amount": 50000,
		"clientOffenceType": "WARNING",
		"warningDescription": "",
		"offence": {"name": "Overloading", "compoundedAmount": 50000},
		"offenceLocation": {"name": "Morogoro"},
	}


def license_page(rows):
	return FakeResponse(200, {"data": {"findMyCurrentLicensesPageable": {"content": rows}}})


def offence_page(rows, total=None):
	return FakeResponse(
		200,
		{"data": {"allMyClientOffencesPageable": {"content": rows, "totalElements": total or len(rows)}}},
	)


def set_latra_settings(username="user@example.com", password="secret", access_token=""):
	settings = frappe.get_single("Latra Settings")
	settings.username = username
	settings.password = password
	settings.access_token = access_token
	settings.save(ignore_permissions=True)
	frappe.cache().delete_value(module._token_cache_key())


class TestLatraHelpers(IntegrationTestCase):
	def test_parse_date(self):
		self.assertIsNone(module._parse_date(None))
		self.assertEqual(module._parse_date("2026-01-05T00:00:00"), "2026-01-05")
		self.assertEqual(module._parse_date("2026-01-05"), "2026-01-05")

	def test_place_issued_and_license_type(self):
		row = license_row("T444LLL", "L1", "2026-12-31")
		self.assertEqual(module._get_place_issued(row), "Dar (Ilala)")
		self.assertEqual(module._get_place_issued({"licenseInfoDetail": {}}), "")
		self.assertEqual(module._get_license_type(row), "GCV")
		self.assertEqual(module._get_license_type(license_row("x", "y", "z", "PRIVATEHIRE")), "Private Hire")
		self.assertEqual(module._get_license_type(license_row("x", "y", "z", "OTHER")), "OTHER")

	def test_log_sync_summary(self):
		with patch("frappe.log_error") as log_error:
			module._log_sync_summary({"message": "a"}, "b")
		log_error.assert_called_once_with(title="LATRA Sync Summary", message="Licenses: a\nOffences: b")


class TestLatraToken(IntegrationTestCase):
	def setUp(self):
		set_latra_settings()

	def test_get_token_reads_settings_and_caches(self):
		self.assertEqual(module._get_token(), "")
		set_latra_settings(access_token=" tok ")
		self.assertEqual(module._get_token(), "tok")
		frappe.db.set_single_value("Latra Settings", "access_token", "other")
		self.assertEqual(module._get_token(), "tok")

	def test_get_token_logs_errors(self):
		with (
			patch("frappe.db.get_single_value", side_effect=RuntimeError("db")),
			patch("frappe.log_error") as log,
		):
			self.assertIsNone(module._get_token())
		log.assert_called_once()

	def test_refresh_token_without_credentials(self):
		frappe.db.set_single_value("Latra Settings", "username", "")
		with patch("frappe.log_error") as log_error:
			self.assertIsNone(module._refresh_token_locked())
		self.assertEqual(log_error.call_args.kwargs["title"], "LATRA: Credentials missing")

	def test_refresh_token_success(self):
		response = FakeResponse(200, {"data": {"accessToken": " new-token "}})
		with patch("requests.post", return_value=response) as post:
			self.assertEqual(module._refresh_token(), "new-token")
		self.assertEqual(
			post.call_args.kwargs["data"], {"username": "user@example.com", "password": "secret"}
		)
		self.assertEqual(frappe.db.get_single_value("Latra Settings", "access_token"), "new-token")
		self.assertEqual(module._get_token(), "new-token")

	def test_refresh_token_failures(self):
		with patch("requests.post", return_value=FakeResponse(401, {}, text="denied")):
			self.assertIsNone(module._refresh_token_locked())
		with patch("requests.post", return_value=FakeResponse(200, {"data": {}})):
			self.assertIsNone(module._refresh_token_locked())
		with patch("requests.post", side_effect=requests.exceptions.ConnectionError("down")):
			self.assertIsNone(module._refresh_token_locked())

	def test_refresh_token_reuses_token_refreshed_by_another_worker(self):
		set_latra_settings(access_token="fresh")
		with patch("requests.post") as post:
			self.assertEqual(module._refresh_token(old_token="stale"), "fresh")
		post.assert_not_called()


class TestLatraApiCalls(IntegrationTestCase):
	def test_call_license_page_statuses(self):
		with patch("requests.post", return_value=license_page([{"licenseNumber": "L1"}])):
			self.assertEqual(
				module._call_license_page("tok"),
				{"findMyCurrentLicensesPageable": {"content": [{"licenseNumber": "L1"}]}},
			)
		with patch("requests.post", return_value=FakeResponse(401, {})):
			self.assertEqual(module._call_license_page("tok"), TOKEN_EXPIRED)
		with patch("requests.post", return_value=FakeResponse(429, {})):
			self.assertEqual(module._call_license_page("tok"), "RATE_LIMITED")
		with patch("requests.post", return_value=FakeResponse(500, {})):
			self.assertIsNone(module._call_license_page("tok"))
		with patch("requests.post", return_value=FakeResponse(400, {})), patch("frappe.log_error") as log:
			self.assertIsNone(module._call_license_page("tok"))
		log.assert_called_once()
		with patch("requests.post", side_effect=requests.exceptions.Timeout()):
			self.assertIsNone(module._call_license_page("tok"))
		with patch("requests.post", return_value=FakeResponse(200, {"errors": [{"message": "bad"}]})):
			self.assertIsNone(module._call_license_page("tok"))
		with patch("requests.post", return_value=FakeResponse(200, None, text="<html>")):
			self.assertIsNone(module._call_license_page("tok"))

	def test_fetch_all_licenses_paginates(self):
		first = [license_row("T444LLL", f"L{i}", "2026-12-31") for i in range(200)]
		second = [license_row("T555LLL", "L200", "2026-12-31")]
		with patch("requests.post", side_effect=[license_page(first), license_page(second)]) as post:
			rows = module._fetch_all_licenses("tok")
		self.assertEqual(len(rows), 201)
		self.assertEqual(post.call_count, 2)
		self.assertEqual(post.call_args_list[1].kwargs["json"]["variables"]["pageableParam"]["first"], 1)

		with patch("requests.post", return_value=FakeResponse(401, {})):
			self.assertEqual(module._fetch_all_licenses("tok"), TOKEN_EXPIRED)

	def test_call_offences_page_statuses(self):
		with patch("requests.post", return_value=offence_page([offence_row("T444LLL", "R1")])):
			result = module._call_offences_graphql_page("tok")
		self.assertEqual(result["allMyClientOffencesPageable"]["totalElements"], 1)
		with patch("requests.post", return_value=FakeResponse(401, {})):
			self.assertEqual(module._call_offences_graphql_page("tok"), TOKEN_EXPIRED)
		with patch("requests.post", return_value=FakeResponse(429, {})):
			self.assertEqual(module._call_offences_graphql_page("tok"), "RATE_LIMITED")
		with patch("requests.post", return_value=FakeResponse(503, {})):
			self.assertIsNone(module._call_offences_graphql_page("tok"))
		with patch("requests.post", return_value=FakeResponse(403, {})):
			self.assertIsNone(module._call_offences_graphql_page("tok"))
		with patch("requests.post", side_effect=requests.exceptions.ConnectionError()):
			self.assertIsNone(module._call_offences_graphql_page("tok"))
		with patch("requests.post", side_effect=requests.exceptions.InvalidURL()):
			self.assertIsNone(module._call_offences_graphql_page("tok"))
		with patch("requests.post", return_value=FakeResponse(200, {"errors": ["x"]})):
			self.assertIsNone(module._call_offences_graphql_page("tok"))
		with patch("requests.post", return_value=FakeResponse(200, None, text="oops")):
			self.assertIsNone(module._call_offences_graphql_page("tok"))

	def test_fetch_all_offences_paginates(self):
		first = [offence_row("T444LLL", f"R{i}") for i in range(500)]
		second = [offence_row("T444LLL", "R500")]
		with patch("requests.post", side_effect=[offence_page(first, 501), offence_page(second, 501)]):
			rows = module._fetch_all_offences("tok")
		self.assertEqual(len(rows), 501)
		with patch("requests.post", return_value=offence_page([])):
			self.assertEqual(module._fetch_all_offences("tok"), [])
		with patch("requests.post", return_value=FakeResponse(429, {})):
			self.assertEqual(module._fetch_all_offences("tok"), "RATE_LIMITED")


class TestLatraLicenseSync(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.commit_patch = patch.object(frappe.db, "commit")
		cls.commit_patch.start()
		cls.addClassCleanup(cls.commit_patch.stop)
		cls.plates_patch = patch.object(module, "get_unique_vehicle_plates", return_value=list(PLATES))
		cls.plates_patch.start()
		cls.addClassCleanup(cls.plates_patch.stop)

	def setUp(self):
		set_latra_settings(access_token="tok")

	def test_sync_all_latra_licenses_upserts_latest_license(self):
		rows = [
			license_row("t 444 lll", "LIC-OLD", "2026-06-30"),
			license_row("T444LLL", "LIC-NEW", "2027-06-30"),
			license_row("T999ZZZ", "LIC-OTHER", "2027-06-30"),
			{"licenseNumber": "LIC-NOVEHICLE"},
		]
		with patch("requests.post", return_value=license_page(rows)):
			result = sync_all_latra_licenses("tok")
		self.assertEqual(
			(result["matched"], result["skipped"], result["saved"], result["processed"]), (1, 1, 1, 2)
		)
		self.assertTrue(result["completed_cycle"])
		license_doc = frappe.get_doc("Latra Licenses", "LIC-NEW")
		self.assertEqual(license_doc.vehicle, "T444LLL")
		self.assertEqual(license_doc.license_type, "GCV")
		self.assertEqual(license_doc.service_type, "Cargo")
		self.assertEqual(license_doc.place_issued, "Dar (Ilala)")
		self.assertEqual(str(license_doc.expire_date), "2027-06-30")
		self.assertFalse(frappe.db.exists("Latra Licenses", "LIC-OLD"))

		rows[1]["licenseStatus"] = "EXPIRED"
		with patch("requests.post", return_value=license_page(rows)):
			result = sync_all_latra_licenses("tok")
		self.assertEqual(result["saved"], 1)
		self.assertEqual(frappe.db.get_value("Latra Licenses", "LIC-NEW", "license_status"), "EXPIRED")

	def test_sync_all_latra_licenses_propagates_api_state(self):
		with patch("requests.post", return_value=FakeResponse(401, {})):
			self.assertEqual(sync_all_latra_licenses("tok"), TOKEN_EXPIRED)
		with patch("requests.post", return_value=FakeResponse(500, {})):
			self.assertIsNone(sync_all_latra_licenses("tok"))

	def test_upsert_latra_license_edge_cases(self):
		self.assertEqual(module._upsert_latra_license("T444LLL", {}), 0)
		with patch("frappe.db.exists", side_effect=RuntimeError("db")), patch("frappe.log_error") as log:
			self.assertEqual(module._upsert_latra_license("T444LLL", {"licenseNumber": "X"}), 0)
		log.assert_called_once()

	def test_update_latra_records_flow(self):
		set_latra_settings(access_token="")
		with patch.object(module, "_refresh_token", return_value=None):
			self.assertIn("no token", update_latra_records()["message"])

		set_latra_settings(access_token="tok")
		with patch(
			"requests.post", return_value=license_page([license_row("T444LLL", "LIC-A", "2027-01-01")])
		):
			result = update_latra_records()
		self.assertEqual(result["licenses"]["saved"], 1)

		with (
			patch.object(module, "sync_all_latra_licenses", return_value=TOKEN_EXPIRED),
			patch.object(module, "_refresh_token", return_value=None),
		):
			self.assertIn("token refresh failed", update_latra_records()["message"])
		with (
			patch.object(module, "sync_all_latra_licenses", return_value=TOKEN_EXPIRED),
			patch.object(module, "_refresh_token", return_value="tok2"),
		):
			self.assertIn("auth failure", update_latra_records()["message"])
		with patch.object(module, "sync_all_latra_licenses", return_value="RATE_LIMITED"):
			self.assertIn("throttling", update_latra_records()["message"])

	def test_notify_latra_license_expiry(self):
		configure_authority_notifications(["LATRA License"], latra_license_notify_before_days=7)
		for number, days in (("LIC-EXPIRED", -1), ("LIC-SOON", 3), ("LIC-FAR", 30)):
			frappe.get_doc(
				{
					"doctype": "Latra Licenses",
					"license_number": number,
					"vehicle": "T444LLL",
					"expire_date": add_days(nowdate(), days),
				}
			).insert()
		frappe.get_doc({"doctype": "Latra Licenses", "license_number": "LIC-NODATE"}).insert()

		with patch("frappe.sendmail") as sendmail:
			notify_latra_license_expiry()
		self.assertEqual(sendmail.call_count, 2)
		subjects = sorted(call.kwargs["subject"] for call in sendmail.call_args_list)
		self.assertTrue(subjects[0].startswith("LATRA License Expired"))
		self.assertTrue(subjects[1].startswith("LATRA License Expiry Reminder"))
		self.assertTrue(
			frappe.db.get_value(
				"Latra Licenses", "LIC-EXPIRED", "authority_last_expiry_notification_key"
			).startswith("expired:")
		)
		self.assertIsNone(
			frappe.db.get_value("Latra Licenses", "LIC-FAR", "authority_last_expiry_notification_key")
		)

		with patch("frappe.sendmail") as sendmail:
			notify_latra_license_expiry()
		sendmail.assert_not_called()


class TestLatraOffenceSync(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.commit_patch = patch.object(frappe.db, "commit")
		cls.commit_patch.start()
		cls.addClassCleanup(cls.commit_patch.stop)

	def setUp(self):
		set_latra_settings(access_token="tok")
		frappe.db.delete("Latra Offence")

	def test_update_latra_offences_without_plates(self):
		with patch.object(module, "get_unique_vehicle_plates", return_value=[]):
			result = update_latra_offences()
		self.assertEqual(result["processed"], 0)
		self.assertTrue(result["completed_cycle"])

	def test_update_latra_offences_creates_updates_and_notifies(self):
		configure_authority_notifications(
			["LATRA Offence"], latra_offence_notify_on_new=1, latra_offence_notify_on_status_change=1
		)
		rows = [
			offence_row("t-444-lll", "REF-1"),
			offence_row("T444LLL", "REF-2"),
			offence_row("T888ZZZ", "REF-3"),
		]
		with (
			patch.object(module, "get_unique_vehicle_plates", return_value=list(PLATES)),
			patch("requests.post", return_value=offence_page(rows)),
			patch("frappe.sendmail") as sendmail,
		):
			result = update_latra_offences()
		self.assertEqual(
			(result["processed"], result["saved"], result["skipped"], result["matched"]), (2, 2, 1, 1)
		)
		self.assertEqual(result["fetched_offences"], 3)
		self.assertEqual(sendmail.call_count, 2)
		self.assertEqual(sendmail.call_args.kwargs["recipients"], [AUTHORITY_USER])

		offence = frappe.get_doc("Latra Offence", {"reference_number": "REF-1"})
		self.assertEqual(offence.mv_reg_number, "T444LLL")
		self.assertEqual(offence.offence, "Overloading")
		self.assertEqual(offence.location, "Morogoro")
		self.assertEqual(str(offence.offence_date), "2026-02-01")
		self.assertEqual(offence.amount, 50000)
		self.assertEqual(offence.authority_last_notified_status, "UNPAID")
		self.assertIsNotNone(offence.authority_notified_on_new)

		rows[0]["paymentStatus"] = "PAID"
		with (
			patch.object(module, "get_unique_vehicle_plates", return_value=list(PLATES)),
			patch("requests.post", return_value=offence_page(rows)),
			patch("frappe.sendmail") as sendmail,
		):
			result = update_latra_offences()
		self.assertEqual(result["saved"], 2)
		self.assertEqual(frappe.db.count("Latra Offence"), 2)
		sendmail.assert_called_once()
		self.assertIn("from UNPAID to PAID", sendmail.call_args.kwargs["message"])
		offence.reload()
		self.assertEqual(offence.status, "PAID")
		self.assertEqual(offence.authority_last_notified_status, "PAID")

	def test_update_latra_offences_api_failures(self):
		with patch.object(module, "get_unique_vehicle_plates", return_value=list(PLATES)):
			with patch("requests.post", return_value=FakeResponse(429, {})):
				self.assertIn("throttling", update_latra_offences()["message"])
			with patch("requests.post", return_value=FakeResponse(500, {})), patch("frappe.log_error"):
				self.assertIn("upstream failure", update_latra_offences()["message"])
			with (
				patch("requests.post", return_value=FakeResponse(401, {})),
				patch.object(module, "_refresh_token", return_value=None),
				patch("frappe.log_error"),
			):
				self.assertIn("upstream failure", update_latra_offences()["message"])
			set_latra_settings(access_token="")
			with patch.object(module, "_refresh_token", return_value=None), patch("frappe.log_error"):
				self.assertIn("no token", update_latra_offences()["message"])

	def test_send_pending_latra_offence_notifications(self):
		configure_authority_notifications(
			["LATRA Offence"], latra_offence_notify_on_new=1, latra_offence_notify_on_status_change=1
		)
		offence = frappe.get_doc(
			{
				"doctype": "Latra Offence",
				"mv_reg_number": "T444LLL",
				"reference_number": "REF-P",
				"status": "UNPAID",
				"amount": 10,
			}
		).insert()
		frappe.db.set_value("Latra Offence", offence.name, "authority_last_notified_status", "PENDING")
		with patch("frappe.sendmail") as sendmail:
			send_pending_latra_offence_notifications()
		self.assertEqual(sendmail.call_count, 2)
		offence.reload()
		self.assertIsNotNone(offence.authority_notified_on_new)
		self.assertEqual(offence.authority_last_notified_status, "UNPAID")

	def test_notify_latra_offence_disabled_events(self):
		configure_authority_notifications(["LATRA Offence"])
		with patch("frappe.sendmail") as sendmail:
			module._notify_latra_offence("x", {"status": "UNPAID"}, is_new=True)
			module._notify_latra_offence("x", {"status": "PAID"}, is_new=False, old_status="UNPAID")
			module._notify_latra_offence("x", {"status": "PAID"}, is_new=False, old_status="PAID")
		sendmail.assert_not_called()
