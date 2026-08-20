from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	fields = {
		"Customer": [
			dict(
				fieldname="csf_tz_close_dn_section_break",
				fieldtype="Section Break",
				label="Auto Close Dn",
				insert_after="companies",
			),
			dict(
				fieldname="csf_tz_is_auto_close_dn",
				fieldtype="Check",
				label="Is Auto Close Dn",
				insert_after="csf_tz_close_dn_section_break",
				bold=1,
			),
			dict(
				fieldname="csf_tz_close_dn_after",
				fieldtype="Int",
				label="Close Dn after",
				insert_after="csf_tz_is_auto_close_dn",
				description="Delivery notes for this customer will automatically be closed after days specified at this field",
				depends_on="eval:doc.csf_tz_is_auto_close_dn == 1",
				mandatory_depends_on="eval: doc.csf_tz_is_auto_close_dn == 1",
			),
		]
	}

	create_custom_fields(fields, update=True)
