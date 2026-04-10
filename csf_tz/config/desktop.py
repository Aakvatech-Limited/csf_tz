# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"module_name": "CSF TZ",
			"category": "Modules",
			"label": _("Country Specifics"),
			"color": "green",
			"icon": "octicon octicon-bookmark",
			"type": "module",
			"description": "Country specific customizations for compliance, taxation and statutory reports.",
		},
		{
			"module_name": "Purchase and Stock Management",
			"category": "Modules",
			"label": _("Purchase and Stock Management"),
			"color": "green",
			"icon": "octicon octicon-bookmark",
			"type": "module",
		},
		{
			"module_name": "Sales and Marketing",
			"category": "Modules",
			"label": _("Sales and Marketing"),
			"color": "green",
			"icon": "octicon octicon-bookmark",
			"type": "module",
		},
		{
			"module_name": "VFD Providers",
			"category": "Modules",
			"label": _("VFD Providers"),
			"color": "green",
			"icon": "octicon octicon-bookmark",
			"type": "module",
			"description": "VFD provider setup, posting logs, and provider-specific settings.",
		},
		{
			"module_name": "VFD Settings",
			"category": "Modules",
			"label": _("VFD Settings"),
			"color": "green",
			"icon": "octicon octicon-bookmark",
			"type": "module",
			"description": "Company-level VFD provider mapping and controls.",
		},
	]
