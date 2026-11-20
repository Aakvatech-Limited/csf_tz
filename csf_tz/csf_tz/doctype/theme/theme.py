# Copyright (c) 2020, Aakvatech and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class Theme(Document):
	def validate(self):
		csf_theme = open("../apps/csf_tz/csf_tz/public/css/theme.css", "w+")
		csf_theme.write(self.theme)
		csf_theme.close()
