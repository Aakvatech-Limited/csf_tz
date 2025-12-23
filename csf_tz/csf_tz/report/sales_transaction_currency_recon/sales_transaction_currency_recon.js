// Copyright (c) 2025, Aakvatech and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Transaction Currency Recon"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "view",
			label: __("View"),
			fieldtype: "Select",
			options: ["Detailed", "Grouped by Customer"],
			default: "Detailed",
			reqd: 1,
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		// Calmer pastel palette (sober)
		const COLORS = {
			SO_CLOSED: "#F8D7DA",   // soft rose
			SO_HOLD: "#FFF3CD",   // soft amber
			SO_OTHER: "#D1F2EB",   // soft mint
			SI: "#FFFBE6",   // soft cream
			PE: "#DFF5E1",   // soft teal/green (slightly more visible)
		};

		const wrap = (html, background) => {
			return `<span style="
      display:block;
      padding:2px 4px;
      background:${background};
      color:#000;
      border-radius:2px;
    ">${html}</span>`;
		};

		if (data.doc_type === "Payment Entry") {
			return wrap(value, COLORS.PE);
		}

		if (data.doc_type === "Sales Invoice") {
			return wrap(value, COLORS.SI);
		}

		if (data.doc_type === "Sales Order") {
			if (data.status === "Closed") return wrap(value, COLORS.SO_CLOSED);
			if (data.status === "On Hold") return wrap(value, COLORS.SO_HOLD);
			return wrap(value, COLORS.SO_OTHER);
		}

		return value;
	}
};
