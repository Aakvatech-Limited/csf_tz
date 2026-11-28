frappe.ui.form.on("Pergamon VFD Settings", {
  refresh(frm) {
    if (frm.is_new()) return;
    frm.add_custom_button(__("Fetch Daily Z Report"), () => {
      frappe.prompt(
        [{
          fieldname: "report_date",
          label: __("Report Date"),
          fieldtype: "Date",
          default: frappe.datetime.get_today(),
          reqd: 1,
        }],
        (values) => {
          frappe.call({
            method: "csf_tz.vfd_providers.doctype.pergamon_vfd_settings.pergamon_vfd_settings.fetch_pergamon_zreport",
            args: { company: frm.doc.company, report_date: values.report_date },
            freeze: true,
            freeze_message: __("Retrieving Pergamon Z Report..."),
          }).then((r) => {
            const result = r.message || {};
            if (result.z_report) {
              frappe.show_alert({
                message: __("Pergamon Z Report archived: {0}", [result.z_report]),
                indicator: "green",
              });
              frappe.set_route("Form", "VFD Z Report", result.z_report);
            }
          });
        },
        __("Retrieve Daily Z Report"),
        __("Fetch")
      );
    }, __("Reports"));
    frm.add_custom_button(__("Fetch Periodic Report"), () => {
      frappe.prompt(
        [
          {fieldname: "from_date", fieldtype: "Date", label: __("From Date"), reqd: 1},
          {fieldname: "to_date", fieldtype: "Date", label: __("To Date"), reqd: 1},
        ],
        (values) => {
          if (values.from_date > values.to_date) {
            frappe.msgprint(__("From Date must not be after To Date"));
            return;
          }
          frappe.call({
            method: "csf_tz.vfd_providers.doctype.pergamon_vfd_settings.pergamon_vfd_settings.fetch_pergamon_periodic_report",
            args: {
              company: frm.doc.company,
              from_date: values.from_date,
              to_date: values.to_date,
            },
            freeze: true,
            freeze_message: __("Retrieving Pergamon periodic report..."),
          }).then((r) => {
            const result = r.message || {};
            if (result.periodic_report) {
              frappe.show_alert({
                message: __("Pergamon Periodic Report archived: {0}", [result.periodic_report]),
                indicator: "green",
              });
              frappe.set_route("Form", "VFD Periodic Report", result.periodic_report);
            }
          });
        },
        __("Retrieve Periodic Report"),
        __("Fetch")
      );
    }, __("Reports"));
  },
});
