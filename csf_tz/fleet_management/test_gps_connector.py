from frappe.tests.utils import FrappeTestCase


class TestGpsConnector(FrappeTestCase):
	def test_get_last_location_uses_parameterised_query(self):
		"""Original code built the WHERE clause by string concatenation:
		'... WHERE ... = UPPER(\\'' + vehicle_plate_no + '\\')'
		which allows SQL injection. Fixed: uses a %s placeholder."""
		import inspect

		from csf_tz.fleet_management.gps_connector import get_last_location

		source = inspect.getsource(get_last_location)
		# The parameterised form must be present
		self.assertIn("%s", source)
		# The vulnerable string concatenation must be absent
		self.assertNotIn("+ vehicle_plate_no +", source)

	def test_endpoints_require_authentication(self):
		"""All four GPS endpoints must not carry allow_guest=True.
		Unauthenticated callers must not be able to mutate vehicle data
		or trigger Postgres queries."""
		import inspect

		from csf_tz.fleet_management import gps_connector

		for name in (
			"get_last_location",
			"load_cargo",
			"offload_cargo",
			"loop_through_vehicles",
		):
			func = getattr(gps_connector, name)
			source = inspect.getsource(func)
			self.assertNotIn(
				"allow_guest=True",
				source,
				msg=f"{name} must not carry allow_guest=True",
			)
