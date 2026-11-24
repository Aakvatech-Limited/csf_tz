"""Register legacy VFD provider defaults without company credentials."""

import frappe

PROVIDERS = (
	(
		"TotalVFD",
		"Total VFD Setting",
		"total_vfd_setting",
		"https://api.totalvfd.co.tz",
		{"sales": "/sales"},
	),
	(
		"VFDPlus",
		"VFDPlus Settings",
		"vfdplus_settings",
		"https://app.vfdplus.co.tz",
		{
			"post_fiscal_receipt": "/vfd-thirdparty-api/post_fiscal_receipt",
			"receipt_info": "/vfd-thirdparty-api/receipt_info",
			"account_info": "/vfd-thirdparty-api/account_info",
			"serial_info": "/vfd-thirdparty-api/serial_info",
		},
	),
	(
		"SimplifyVFD",
		"Simplify VFD Settings",
		"simplify_vfd_settings",
		"https://simplify.co.tz/partner/v1",
		{
			"login": "/auth/user/login",
			"refresh": "/auth/user/token/refresh",
			"createIssuedInvoice": "/invoice/createIssuedInvoice",
		},
	),
)


def execute():
	for name, settings, module, base_url, endpoints in PROVIDERS:
		if frappe.db.exists("VFD Provider", {"vfd_provider": name}):
			continue
		frappe.get_doc(
			{
				"doctype": "VFD Provider",
				"vfd_provider": name,
				"vfd_provider_settings": settings,
				"vfd_provider_controller": f"csf_tz.vfd_providers.doctype.{module}.{module}",
				"base_url": base_url,
				"attributes": [{"key": key, "value": value} for key, value in endpoints.items()],
			}
		).insert(ignore_permissions=True)
