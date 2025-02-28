frappe.require([
  "/assets/csf_tz/js/csfUtlis.js",
  "/assets/csf_tz/js/shortcuts.js",
]);

frappe.ui.form.on("Sales Invoice", {
  refresh: function (frm) {
    const limit_uom_as_item_uom = getValue(
      "CSF TZ Settings",
      "CSF TZ Settings",
      "limit_uom_as_item_uom"
    );
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
    frm.trigger("set_pos");
    frm.trigger("make_sales_invoice_btn");
    frm.trigger("set_trade_in_field_visibility");
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
    frm.trigger("set_trade_in_field_visibility");
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

  // Trade In Feature
  set_trade_in_field_visibility: function (frm) {
    // Fetch the Enable Trade In setting from CSF TZ Settings using get_single_value
    frappe.db
      .get_single_value("CSF TZ Settings", "enable_trade_in")
      .then((enable_trade_in) => {
        // Show or hide the Custom Is Trade-In checkbox based on the setting
        frm.set_df_property("custom_is_trade_in", "hidden", !enable_trade_in);
      });
  },

  custom_is_trade_in: function (frm) {
    if (frm.doc.custom_is_trade_in) {
      frappe.db
        .get_value("Company", frm.doc.company, [
          "custom_trade_in_control_account",
        ])
        .then((company_res) => {
          const trade_in_account =
            company_res?.message?.custom_trade_in_control_account;
          if (!trade_in_account)
            frappe.throw(
              "Trade-In Control Account is not set in Company settings."
            );

          if (!frm.doc.items.some((item) => item.item_code === "Trade In")) {
            frm.add_child("items", {
              item_code: "Trade In",
              item_name: "Trade In",
              income_account: trade_in_account,
              qty: 1,
              description: "Trade-In",
            });
            frm.refresh_field("items");
          }
        });
    } else {
      frappe.confirm(
        'Are you sure you want to remove the "Trade In" item?',
        () => {
          frm.doc.items = frm.doc.items.filter(
            (item) => item.item_code !== "Trade In"
          );
          frm.refresh_field("items");
        },
        () => frm.set_value("custom_is_trade_in", 1)
      );
    }
  },
});

frappe.ui.form.on("Sales Invoice Item", {
  item_code: function (frm, cdt, cdn) {
    validate_item_remaining_qty(frm, cdt, cdn);
  },
  qty: function (frm, cdt, cdn) {
    validate_item_remaining_qty(frm, cdt, cdn);
  },
  stock_qty: function (frm, cdt, cdn) {
    validate_item_remaining_stock_qty(frm, cdt, cdn);
  },
  uom: function (frm, cdt, cdn) {
    validate_item_remaining_qty(frm, cdt, cdn);
  },
  allow_over_sell: function (frm, cdt, cdn) {
    validate_item_remaining_stock_qty(frm, cdt, cdn);
  },
  conversion_factor: function (frm, cdt, cdn) {
    validate_item_remaining_stock_qty(frm, cdt, cdn);
  },
  warehouse: function (frm, cdt, cdn) {
    validate_item_remaining_stock_qty(frm, cdt, cdn);
  },
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
  // Trade In Feature
  custom_trade_in_qty: function (frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    calculate_row_trade_in_value(frm, cdt, cdn);
  },
  custom_trade_in_item: function (frm, cdt, cdn) {
    // Reset serial numbers when item changes
    frappe.model.set_value(cdt, cdn, "custom_trade_in_serial_no", "");
  },
  custom_trade_in_incoming_rate: function (frm, cdt, cdn) {
    calculate_row_trade_in_value(frm, cdt, cdn);
  },
  item_code: function (frm, cdt, cdn) {
    set_trade_in_fields_readonly(frm);
  },
  form_render(frm, cdt, cdn) {
    // Get the current child table row document
    let row = locals[cdt][cdn];

    // Debugging: Log the row and frm
    // console.log("Row data:", row);
    // console.log("Form data:", frm);

    // Ensure row is defined before calling the function
    if (row) {
      set_trade_in_fields_readonly(frm, row);
    } else {
      // console.error("Row is undefined.");
    }
  },
});

var validate_item_remaining_qty = function (frm, cdt, cdn) {
  const item_row = locals[cdt][cdn];
  if (item_row.item_code == null) {
    return;
  }
  if (item_row.allow_over_sell == 1) {
    return;
  }
  const conversion_factor = get_conversion_factor(
    item_row,
    item_row.item_code,
    item_row.uom
  );
  frappe.call({
    method: "csf_tz.custom_api.validate_item_remaining_qty",
    args: {
      item_code: item_row.item_code,
      company: frm.doc.company,
      warehouse: item_row.warehouse,
      stock_qty: item_row.qty * conversion_factor,
      so_detail: item_row.so_detail,
    },
    async: false,
  });
};

var validate_item_remaining_stock_qty = function (frm, cdt, cdn) {
  const item_row = locals[cdt][cdn];
  if (item_row.item_code == null) {
    return;
  }
  if (item_row.allow_over_sell == 1) {
    return;
  }
  frappe.call({
    method: "csf_tz.custom_api.validate_item_remaining_qty",
    args: {
      item_code: item_row.item_code,
      company: frm.doc.company,
      warehouse: item_row.warehouse,
      stock_qty: item_row.stock_qty,
    },
    async: false,
  });
};

var get_conversion_factor = function (item_row, item_code, uom) {
  if (item_code && uom) {
    let conversion_factor = 0;
    frappe.call({
      method: "erpnext.stock.get_item_details.get_conversion_factor",
      child: item_row,
      args: {
        item_code: item_code,
        uom: uom,
      },
      async: false,
      callback: function (r) {
        if (!r.exc) {
          conversion_factor = r.message.conversion_factor;
        }
      },
    });
    return conversion_factor;
  }
};

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

// Calculate custom_total_trade_in_value for a specific row in the items child table
function calculate_row_trade_in_value(frm, cdt, cdn) {
  let row = locals[cdt][cdn];

  // Calculate custom_total_trade_in_value as custom_trade_in_qty * custom_trade_in_incoming_rate
  let total_value =
    (row.custom_trade_in_qty || 0) * (row.custom_trade_in_incoming_rate || 0);
  frappe.model.set_value(cdt, cdn, "custom_total_trade_in_value", total_value);

  // Set rate field as negative
  frappe.model.set_value(cdt, cdn, "rate", total_value * -1); // Set rate to negative value
}
// Function to set trade-in fields read-only based on conditions
function set_trade_in_fields_readonly(frm, row) {
  // Log the item code for debugging
  if (!row || !row.item_code) {
    //console.error("Row or item_code is undefined.");
    return; // Exit if row or item_code is not defined
  }

  //console.log("Checking item code:", row.item_code);

  if (row.item_code === "Trade In") {
    //console.log("Trade In item found in child table.");

    // Set fields to read-only for the "Trade In" item
    frm.fields_dict.items.grid.update_docfield_property(
      "item_name",
      "read_only",
      1,
      row.idx
    );
    frm.fields_dict.items.grid.update_docfield_property(
      "rate",
      "read_only",
      1,
      row.idx
    );
    frm.fields_dict.items.grid.update_docfield_property(
      "posa_special_discount",
      "read_only",
      1,
      row.idx
    );
    frm.fields_dict.items.grid.update_docfield_property(
      "posa_special_rate",
      "read_only",
      1,
      row.idx
    );
    frm.fields_dict.items.grid.update_docfield_property(
      "qty",
      "read_only",
      1,
      row.idx
    );
  } else {
    //console.log("Non Trade In item found:", row.item_code);

    // Set fields to editable for non "Trade In" items
    frm.fields_dict.items.grid.update_docfield_property(
      "item_name",
      "read_only",
      0,
      row.idx
    );
    frm.fields_dict.items.grid.update_docfield_property(
      "rate",
      "read_only",
      0,
      row.idx
    );
    frm.fields_dict.items.grid.update_docfield_property(
      "posa_special_discount",
      "read_only",
      0,
      row.idx
    );
    frm.fields_dict.items.grid.update_docfield_property(
      "posa_special_rate",
      "read_only",
      0,
      row.idx
    );
    frm.fields_dict.items.grid.update_docfield_property(
      "qty",
      "read_only",
      0,
      row.idx
    );
  }

  // Refresh the row to reflect the changes
  frm.refresh_field("items");
}
