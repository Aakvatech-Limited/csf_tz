# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe

__version__ = "16.0.0"
app_name = "csf_tz"


def console(*data):
	frappe.publish_realtime("out_to_console", data, user=frappe.session.user)
