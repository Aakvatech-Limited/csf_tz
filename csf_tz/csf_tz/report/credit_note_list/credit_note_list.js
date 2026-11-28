frappe.query_reports["Credit Note List"] = {
    filters: [
        {
            fieldname: "company",
            label: "Company",
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1
        },
        {
            fieldname: "time_span",
            label: "Time Span",
            fieldtype: "Select",
            options: ["Today", "Yesterday", "This Week", "Last Week", "This Month", "Last Month", "Period"],
            default: "This Month",
            reqd: 1
        },
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            depends_on: "eval:doc.time_span == 'Period'",
            mandatory_depends_on: "eval:doc.time_span == 'Period'"
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            depends_on: "eval:doc.time_span == 'Period'",
            mandatory_depends_on: "eval:doc.time_span == 'Period'"
        },
        {
            fieldname: "customer",
            label: "Customer",
            fieldtype: "Link",
            options: "Customer"
        },
        {
            fieldname: "credit_note",
            label: "Credit Note",
            fieldtype: "Link",
            options: "Sales Invoice",
            get_query: () => ({filters: {is_return: 1, docstatus: 1}})
        }
    ]
};
