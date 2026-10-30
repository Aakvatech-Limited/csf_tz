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
  },
});
