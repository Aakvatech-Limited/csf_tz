# Copyright (c) 2023, Aakvatech Limited and contributors
# For license information, please see license.txt

import frappe
from urllib.parse import urlsplit
from frappe import _
from frappe.model.document import Document

# URLs and endpoints of the providers this app talks to, keyed by settings
# doctype because the provider record can be renamed by the user.
PROVIDER_DEFAULTS = {
	"Pergamon VFD Settings": {
		"live_url": None,
		"test_url": "https://5.161.57.127:9040/api/v1",
		"endpoints": {
			"post_receipt": "/invoices",
			"get_invoices": "/invoices",
			"get_invoice": "/invoices/{id}",
			"zreports": "/zreports",
			"periodic_reports": "/periodic-reports",
			"generate_invoices": "/generate-invoices",
		},
	},
	"DIRM VFD Settings": {
		"test_url": "https://dirmvfd.co.tz/api_demo",
		"live_url": "https://dirmvfd.co.tz/api_live",
		"endpoints": {
			"get_token": "/api/v1/session/get_token",
			"post_receipt": "/api/v1/receipts/post",
		},
	},
}


class VFDProvider(Document):
	def before_insert(self):
		self.set_endpoints()

	def validate(self):
		self.set_base_url()

	def set_base_url(self):
		"""Follow the sandbox flag so users never type a URL.

		Providers without known URLs keep the base_url that was entered.
		"""
		defaults = PROVIDER_DEFAULTS.get(self.vfd_provider_settings)
		if not defaults:
			return

		if self.vfd_provider_settings == "Pergamon VFD Settings":
			test_url = str(frappe.conf.get("pergamon_sandbox_url") or defaults["test_url"]).rstrip("/")
			production_url = str(frappe.conf.get("pergamon_production_url") or "").rstrip("/")
			test_host = urlsplit(test_url)
			live_host = urlsplit(production_url)
			if self.sandbox:
				if test_host.scheme != "https" or not test_host.hostname:
					frappe.throw(_("Pergamon sandbox URL must be HTTPS"))
				if production_url and test_host.hostname == live_host.hostname:
					frappe.throw(_("Pergamon sandbox and production must have different hostnames"))
				self.base_url = test_url
			else:
				if live_host.scheme != "https" or not live_host.hostname:
					frappe.throw(_("Configure pergamon_production_url before disabling Pergamon Sandbox"))
				if test_host.hostname == live_host.hostname:
					frappe.throw(_("Pergamon production endpoint must differ from the test endpoint"))
				self.base_url = production_url
			return

		self.base_url = defaults["test_url"] if self.sandbox else defaults["live_url"]

	def set_endpoints(self):
		"""Add the endpoints of a known provider, keeping any the user entered."""
		defaults = PROVIDER_DEFAULTS.get(self.vfd_provider_settings)
		if not defaults:
			return

		entered = {row.key for row in self.attributes}
		for key, value in defaults["endpoints"].items():
			if key not in entered:
				self.append("attributes", {"key": key, "value": value})

	def get_endpoint(self, key):
		"""Endpoint path stored as an attribute of this provider."""
		for row in self.attributes:
			if row.key == key:
				return row.value

		frappe.throw(_("Endpoint {0} is not set in VFD Provider {1}").format(key, self.name))
