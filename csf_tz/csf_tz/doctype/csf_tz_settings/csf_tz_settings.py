# -*- coding: utf-8 -*-
# Copyright (c) 2020, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.installer import update_site_config
from frappe.model.document import Document


class CSFTZSettings(Document):
	def validate(self):
		if self.enable_fixed_working_days_per_month and (
			self.working_days_per_month < 1 or self.working_days_per_month > 30
		):
			frappe.throw(_("Working days per month must be between 1 and 30"))

		if self.override_email_queue_batch_size and self.has_value_changed("email_qatch_batch_size"):
			update_site_config("email_queue_batch_size", self.email_qatch_batch_size)

	def on_update(self):
		self.manage_tz_regions_population()

	def manage_tz_regions_population(self):
		"""Handle TZ Regions data population when checkbox is ticked"""
		if self.populate_tz_regions and self.has_value_changed("populate_tz_regions"):
			try:
				frappe.msgprint(_("Starting TZ Regions data population. This may take several minutes..."))

				# Run the population in the background
				frappe.enqueue(
					method=self.populate_tz_regions_background,
					queue="long",
					timeout=14400,  # 4 hour timeout
					is_async=True,
					job_name="populate_tz_regions",
				)

			except Exception as e:
				frappe.log_error(f"Error starting TZ Regions population: {e!s}")
				frappe.msgprint(_("Failed to start TZ Regions population: {0}").format(str(e)))
				self.db_set("populate_tz_regions", 0)

	def populate_tz_regions_background(self):
		"""Background method to populate TZ regions data"""
		try:
			from csf_tz.patches.tz_post_code.create_tz_post_code import (
				execute as populate_tz_data,
			)

			populate_tz_data()

			# Update the settings to mark as completed
			settings = frappe.get_single("CSF TZ Settings")
			settings.tz_regions_populated = 1
			settings.populate_tz_regions = 0  # Reset the trigger checkbox
			settings.save(ignore_permissions=True)
			frappe.db.commit()

			# Send notification to user
			frappe.publish_realtime(
				event="msgprint",
				message=_("TZ Regions data population completed successfully!"),
				user=frappe.session.user,
			)

		except Exception as e:
			error_msg = f"Error during TZ Regions population: {e!s}"
			frappe.log_error("TZ Regions Population Error", error_msg)

			# Send error notification to user
			frappe.publish_realtime(
				event="msgprint",
				message=_("TZ Regions data population failed: {0}").format(str(e)),
				user=frappe.session.user,
			)

			try:
				settings = frappe.get_single("CSF TZ Settings")
				settings.populate_tz_regions = 0
				settings.tz_regions_populated = 0
				settings.save(ignore_permissions=True)
				frappe.db.commit()
			except Exception:
				pass
