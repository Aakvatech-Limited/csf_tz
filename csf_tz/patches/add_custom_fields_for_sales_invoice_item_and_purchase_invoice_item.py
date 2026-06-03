from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	new_fields = {
		"Purchase Invoice Item": [
			dict(
				fieldname="csf_tz_specifics",
				label="CSF TZ Specifics",
				fieldtype="Section Break",
				insert_after="is_free_item",
			),
			dict(
				fieldname="csf_tz_wtax_jv_created",
				label="CSF TZ Wtax JV Created",
				fieldtype="Check",
				insert_after="csf_tz_specifics",
				read_only=1,
				allow_on_submit=1,
			),
			dict(
				fieldname="csf_tz_wtax_column_break",
				label="",
				fieldtype="Column Break",
				insert_after="csf_tz_wtax_jv_created",
			),
			dict(
				fieldname="csf_tz_create_wtax_entry",
				label="Create WTax Entry",
				fieldtype="Button",
				insert_after="csf_tz_wtax_column_break",
				depends_on="eval: doc.docstatus == 1 && doc.withholding_tax_rate > 0 && doc.csf_tz_wtax_jv_created == 0",
			),
		],
		"Sales Invoice Item": [
			dict(
				fieldname="csf_tz_specifics",
				label="CSF TZ Specifics",
				fieldtype="Section Break",
				insert_after="grant_commission",
			),
			dict(
				fieldname="csf_tz_wtax_jv_created",
				label="CSF TZ Wtax JV Created",
				fieldtype="Check",
				insert_after="csf_tz_specifics",
				read_only=1,
				allow_on_submit=1,
			),
			dict(
				fieldname="csf_tz_wtax_column_break",
				label="",
				fieldtype="Column Break",
				insert_after="csf_tz_wtax_jv_created",
			),
			dict(
				fieldname="csf_tz_create_wtax_entry",
				label="Create WTax Entry",
				fieldtype="Button",
				insert_after="csf_tz_wtax_column_break",
				depends_on="eval: doc.docstatus == 1 && doc.withholding_tax_rate > 0 && doc.csf_tz_wtax_jv_created == 0",
			),
		],
	}

	create_custom_fields(new_fields, update=True)
