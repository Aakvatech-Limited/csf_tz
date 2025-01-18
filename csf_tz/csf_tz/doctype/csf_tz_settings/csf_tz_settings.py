# -*- coding: utf-8 -*-
# Copyright (c) 2020, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.installer import update_site_config
from csf_tz.trade_in.utils import (
    add_trade_in_module,
    add_trade_in_item,
    add_trade_in_control_account,
    delete_trade_in_item_and_account,
    set_negative_rates_for_items
)



class CSFTZSettings(Document):
    def validate(self):
        if self.enable_fixed_working_days_per_month and (
            self.working_days_per_month < 1 or self.working_days_per_month > 30
        ):
            frappe.throw("Working days per month must be between 1 and 30")

        if self.override_email_queue_batch_size and self.has_value_changed(
            "email_qatch_batch_size"
        ):
            update_site_config("email_queue_batch_size", self.email_qatch_batch_size)

    def on_update(self):
        self.manage_trade_in_functionality()

    def manage_trade_in_functionality(self):
        # Check if the feature is being enabled
        if self.enable_trade_in:
            try:
                add_trade_in_module()  # Add Trade In module
                add_trade_in_item()    # Create Trade In item
                add_trade_in_control_account()  # Create Control Account
                set_negative_rates_for_items()  # Create Control Account
                frappe.msgprint("Trade In feature has been successfully enabled.")
            except Exception as e:
                # Log the error and notify the user
                frappe.log_error(f"Error enabling Trade In feature: {str(e)}")
                frappe.msgprint(f"Failed to enable Trade In feature: {str(e)}")
        else:
            # If the feature is being disabled, delete the associated item and account
            try:
                delete_trade_in_item_and_account()  # Delete Trade In item and Control Account
                frappe.msgprint("Trade In feature has been successfully disabled.")
            except Exception as e:
                # Log the error and notify the user
                frappe.log_error(f"Error disabling Trade In feature: {str(e)}")
                frappe.msgprint(f"Failed to disable Trade In feature: {str(e)}")        