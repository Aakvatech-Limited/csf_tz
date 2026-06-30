frappe.require([
  "/assets/csf_tz/js/shortcuts.js",
]);

frappe.ui.form.on("Sales Invoice", {
  refresh: function (frm) {
    frappe.db.get_single_value("CSF TZ Settings", "limit_uom_as_item_uom").then(limit_uom_as_item_uom => {
      if (limit_uom_as_item_uom == 1) {
      frm.set_query("uom", "items", function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        return {
          query:
            "erpnext.accounts.doctype.pricing_rule.pricing_rule.get_item_uoms",
          filters: {
            value: row.item_code,
            apply_on: "Item Code",
          },
        };
      });
      }
    });
    frm.trigger("set_pos");
    frm.trigger("make_sales_invoice_btn");
    frm.trigger("add_write_off_button");
  },
  onload: function (frm) {
    frm.trigger("set_pos");
    if (frm.doc.document_status == "Draft") {
      if (frm.doc.is_return == "0") {
        frm.set_value("naming_series", "ACC-SINV-.YYYY.-");
      } else if (frm.doc.is_return == "1") {
        frm.set_value("naming_series", "ACC-CN-.YYYY.-");
        frm.set_value("select_print_heading", "CREDIT NOTE");
      }
    }
    // frm.trigger("update_stock");
  },
  customer: function (frm) {
    setTimeout(function () {
      if (!frm.doc.customer) {
        return;
      }
      if (!frm.doc.tax_category) {
        frappe.call({
          method: "csf_tz.custom_api.get_tax_category",
          args: {
            doc_type: frm.doc.doctype,
            company: frm.doc.company,
          },
          callback: function (r) {
            if (!r.exc) {
              frm.set_value("tax_category", r.message);
              frm.trigger("tax_category");
            }
          },
        });
      }
    }, 1000);
  },
  default_item_discount: function (frm) {
    frm.doc.items.forEach((item) => {
      frappe.model.set_value(
        item.doctype,
        item.name,
        "discount_percentage",
        frm.doc.default_item_discount
      );
    });
  },
  default_item_tax_template: function (frm) {
    frm.doc.items.forEach((item) => {
      frappe.model.set_value(
        item.doctype,
        item.name,
        "item_tax_template",
        frm.doc.default_item_tax_template
      );
    });
  },
  // update_stock: (frm) => {
  //     const warehouse_field = frappe.meta.get_docfield("Sales Invoice Item", "warehouse", frm.doc.name);
  //     const item_field = frappe.meta.get_docfield("Sales Invoice Item", "item_code", frm.doc.name);
  //     const qty_field = frappe.meta.get_docfield("Sales Invoice Item", "qty", frm.doc.name);
  //     if (frm.doc.update_stock){
  //         warehouse_field.in_list_view = 1;
  //         warehouse_field.idx = 3;
  //         warehouse_field.columns = 2;
  //         item_field.columns =3;
  //         qty_field.columns =1;
  //         refresh_field("items");
  //     }else{
  //         warehouse_field.in_list_view = 0;
  //         warehouse_field.columns = 0;
  //         item_field.columns =4;
  //         qty_field.columns =2;
  //         refresh_field("items");
  //     }
  // },
  make_sales_invoice_btn: function (frm) {
    if (
      frm.doc.docstatus == 1 &&
      frm.doc.enabled_auto_create_delivery_notes == 1
    ) {
      frm.add_custom_button(
        __("Create Delivery Note"),

        function () {
          frappe.call({
            method: "csf_tz.custom_api.create_delivery_note",
            args: {
              doc_name: frm.doc.name,
              method: 1,
            },
          });
        }
      );
    }
  },
  set_pos: function (frm) {
    frappe.db
      .get_value("CSF TZ Settings", {}, "auto_pos_for_role")
      .then((r) => {
        if (r.message) {
          if (
            frappe.user_roles.includes(r.message.auto_pos_for_role) &&
            frm.doc.docstatus == 0 &&
            frappe.session.user != "Administrator" &&
            frm.doc.is_pos != 1
          ) {
            frm.set_value("is_pos", true);
            frm.set_df_property("is_pos", "read_only", true);
          }
        }
      });
  },

  // Write-off Journal Entry Feature
  add_write_off_button: function (frm) {
    // Check if feature is enabled and conditions are met
    frappe.db
      .get_single_value("CSF TZ Settings", "enable_write_off_jv_si")
      .then((enable_write_off) => {
        if (enable_write_off &&
            frm.doc.docstatus === 1 &&
            frm.doc.outstanding_amount > 0 &&
            !frm.doc.is_return) {

          frm.add_custom_button(__("Write Off Outstanding"), function () {
            // Fetch the write-off account from Company before showing the dialog
            frappe.db.get_value("Company", frm.doc.company, "write_off_account").then(function(r) {
              let write_off_account = r.message ? r.message.write_off_account : null;

              // Show dialog to select write-off account
              let dialog = new frappe.ui.Dialog({
                title: __("Write Off Outstanding Amount"),
                fields: [
                  {
                    fieldname: "write_off_account",
                    label: __("Write Off Account"),
                    fieldtype: "Link",
                    options: "Account",
                    "default": write_off_account,
                    reqd: 1,
                    get_query: function() {
                      return {
                        filters: {
                          "report_type": "Balance Sheet",
                          "is_group": 0,
                          "company": frm.doc.company
                        }
                      };
                    }
                  },
                  {
                    fieldname: "outstanding_amount",
                    label: __("Outstanding Amount"),
                    fieldtype: "Currency",
                    default: frm.doc.outstanding_amount,
                    read_only: 1
                  }
                ],
                primary_action_label: __("Create Write Off Entry"),
                primary_action: function(values) {
                  frappe.call({
                    method: "csf_tz.custom_api.create_write_off_jv_si",
                    args: {
                      sales_invoice: frm.doc.name,
                      account: values.write_off_account
                    },
                    callback: function(r) {
                      if (r.message) {
                        const journal_entry_link = `<a href="/desk/journal-entry/${encodeURIComponent(r.message)}" target="_blank">${frappe.utils.escape_html(r.message)}</a>`;
                        frappe.msgprint(__("Write-off Journal Entry created: {0}", [journal_entry_link]));
                        frm.reload_doc();
                      }
                    }
                  });
                  dialog.hide();
                }
              });
              dialog.show();
            });
          }, __("Create"));
        }
      });
  },

});

frappe.ui.form.on("Sales Invoice Item", {
  csf_tz_create_wtax_entry: (frm, cdt, cdn) => {
    frappe
      .call("csf_tz.custom_api.make_withholding_tax_gl_entries_for_sales", {
        doc: frm.doc,
        method: "From Front End",
      })
      .then((r) => {
        frm.refresh();
      });
  },
});

frappe.ui.keys.add_shortcut({
  shortcut: "ctrl+q",
  action: () => {
    ctrlQ("Sales Invoice Item");
  },
  page: this.page,
  description: __("Select Item Warehouse"),
  ignore_inputs: true,
});

frappe.ui.keys.add_shortcut({
  shortcut: "ctrl+i",
  action: () => {
    ctrlI("Sales Invoice Item");
  },
  page: this.page,
  description: __("Select Customer Item Price"),
  ignore_inputs: true,
});

frappe.ui.keys.add_shortcut({
  shortcut: "ctrl+u",
  action: () => {
    ctrlU("Sales Invoice Item");
  },
  page: this.page,
  description: __("Select Item Price"),
  ignore_inputs: true,
});
