frappe.query_reports["Custom Asset Depreciation"] = {
  filters: [
      {
          fieldname: "company",
          label: __("Company"),
          fieldtype: "Link",
          options: "Company",
          default: frappe.defaults.get_user_default("Company"),
          reqd: 1,
      },
      {
          fieldname: "periodicity",
          label: __("Periodicity"),
          fieldtype: "Select",
          options: [
              { value: "Periodicity", label: __("Periodicity") },
              { value: "Quarterly", label: __("Quarterly") },
              { value: "Yearly", label: __("Yearly") }
          ],
          default: "Periodicity",
          reqd: 1,
          on_change: function() {
              let filter_based_on = frappe.query_report.get_filter_value('periodicity');
              
              if(filter_based_on === "Quarterly") {
                  let date = frappe.datetime.get_today();
                  let quarter = Math.floor((frappe.datetime.str_to_obj(date).getMonth() + 3) / 3);
                  
                  let from_date = frappe.datetime.add_months(date, -3);
                  if (quarter === 1) {
                      from_date = frappe.datetime.get_today();
                      from_date = frappe.datetime.add_months(from_date, -3);
                      from_date = frappe.datetime.month_start(from_date);
                  } else if (quarter === 2) {
                      from_date = frappe.datetime.get_today();
                      from_date = frappe.datetime.add_months(from_date, -6);
                      from_date = frappe.datetime.month_start(from_date);
                  } else if (quarter === 3) {
                      from_date = frappe.datetime.get_today();
                      from_date = frappe.datetime.add_months(from_date, -9);
                      from_date = frappe.datetime.month_start(from_date);
                  } else if (quarter === 4) {
                      from_date = frappe.datetime.get_today();
                      from_date = frappe.datetime.add_months(from_date, -12);
                      from_date = frappe.datetime.month_start(from_date);
                  }
                  
                  frappe.query_report.set_filter_value('from_date', from_date);
                  frappe.query_report.set_filter_value('to_date', frappe.datetime.get_today());
              } else if(filter_based_on === "Yearly") {
                  let date = frappe.datetime.get_today();
                  let fiscal_year = frappe.defaults.get_user_default("fiscal_year");
                  
                  if (!fiscal_year) {
                      let from_date = frappe.datetime.add_months(date, -12);
                      from_date = frappe.datetime.year_start(from_date);
                      
                      frappe.query_report.set_filter_value('from_date', from_date);
                      frappe.query_report.set_filter_value('to_date', frappe.datetime.get_today());
                  } else {
                      frappe.db.get_value("Fiscal Year", fiscal_year, ["year_start_date", "year_end_date"], (r) => {
                          if (r) {
                              // For Yearly, set the from_date to the start of the fiscal year
                              // and the to_date to the end of the fiscal year.
                              frappe.query_report.set_filter_value('from_date', r.year_start_date);
                              frappe.query_report.set_filter_value('to_date', r.year_end_date);
                          }
                      });
                  }
              }
          }
      },
      {
          fieldname: "from_date",
          label: __("From Date"),
          fieldtype: "Date",
          default: frappe.datetime.add_months(frappe.datetime.get_today(), -3),
          reqd: 1,
      },
      {
          fieldname: "to_date",
          label: __("To Date"),
          fieldtype: "Date",
          default: frappe.datetime.get_today(),
          reqd: 1,
      },
      {
          fieldname: "asset",
          label: __("Asset"),
          fieldtype: "Link",
          options: "Asset",
      },
      {
          fieldname: "asset_category",
          label: __("Asset Category"),
          fieldtype: "Link",
          options: "Asset Category",
      },

      {
          fieldname: "finance_book",
          label: __("Finance Book"),
          fieldtype: "Link",
          options: "Finance Book",
      },
      {
          fieldname: "include_default_book_assets",
          label: __("Include Default FB Assets"),
          fieldtype: "Check",
          default: 1,
      },
  ],
  columns: [
      { label: __("Asset ID"), fieldname: "asset", fieldtype: "Link", options: "Asset", width: 120 },
      { label: __("Asset Name"), fieldname: "asset_name", fieldtype: "Data", width: 180 },
      { label: __("Depreciation Date"), fieldname: "depreciation_date", fieldtype: "Date", width: 120 },
      { label: __("Depreciation Rate (%)"), fieldname: "depreciation_rate", fieldtype: "Float", width: 120 },
      { label: __("Opening WDV"), fieldname: "opening_wdv", fieldtype: "Currency", width: 140 },
      { label: __("Current Period Depreciation"), fieldname: "depreciation_amount", fieldtype: "Currency", width: 160 },
      { label: __("Closing WDV"), fieldname: "closing_wdv", fieldtype: "Currency", width: 140 },
      { label: __("Depreciation Entry"), fieldname: "depreciation_entry", fieldtype: "Link", options: "Journal Entry", width: 140 },
      { label: __("Asset Category"), fieldname: "asset_category", fieldtype: "Link", options: "Asset Category", width: 120 },
      { label: __("Current Status"), fieldname: "status", fieldtype: "Data", width: 120 },
      { label: __("Purchase Date"), fieldname: "purchase_date", fieldtype: "Date", width: 120 },
  ]
};
