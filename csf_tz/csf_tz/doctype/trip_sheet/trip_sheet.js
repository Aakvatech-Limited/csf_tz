// Copyright (c) 2025, Aakvatech and contributors
// For license information, please see license.txt

frappe.ui.form.on("Trip Sheet", {
  refresh: function (frm) {
    // Dynamically set required fields if status is Completed
    frm.set_df_property("end_km", "reqd", frm.doc.status === "Completed");
    frm.set_df_property(
      "fuel_consumed",
      "reqd",
      frm.doc.status === "Completed"
    );

    // Set query for reference_doctype in child table
    frm.fields_dict["delivery_note"].grid.get_field(
      "reference_doctype"
    ).get_query = function (doc, cdt, cdn) {
      return {
        filters: [
          [
            "name",
            "in",
            [
              "Purchase Order",
              "Delivery Note",
              "Purchase Receipt",
              "Purchase Invoice",
              "Sales Order",
              "Stock Entry",
            ],
          ],
        ],
      };
    };
  },

  status: function (frm) {
    // When status changes, update required fields
    frm.set_df_property("end_km", "reqd", frm.doc.status === "Completed");
    frm.set_df_property(
      "fuel_consumed",
      "reqd",
      frm.doc.status === "Completed"
    );
  },

  driver: function (frm) {
    if (frm.doc.driver) {
      frappe.db.get_value(
        "Employee",
        frm.doc.driver,
        "employee_name",
        function (r) {
          frm.set_value("driver_name", r.employee_name);
        }
      );
    } else {
      frm.set_value("driver_name", "");
    }
  },

  // Custom function to fetch items from selected reference documents
  fetch_reference_items: function (frm) {
    // Clear the table first
    frm.clear_table("item_reference");

    // Loop through delivery_note child table
    (frm.doc.delivery_note || []).forEach(function (row) {
      if (row.reference_doctype && row.reference_document) {
        frappe.call({
          method:
            "csf_tz.csf_tz.doctype.trip_sheet.trip_sheet.get_reference_items",
          args: {
            reference_doctype: row.reference_doctype,
            reference_document: row.reference_document,
          },
          callback: function (r) {
            if (r.message && Array.isArray(r.message)) {
              // Add all items for this reference doc
              r.message.forEach(function (item) {
                // Add child and set reference_doctype first
                var child = frm.add_child("item_reference");
                child.reference_doctype = row.reference_doctype;
                // then set the dynamic link field
                child.reference_document_id = row.reference_document;
                child.item_name = item.item_name;
                child.qty = item.qty;
                child.amount = item.amount;
              });
              // refresh once after adding items
              frm.refresh_field("item_reference");
            }
          },
        });
      }
    });
  },
});

// For filtering Stock Entry by stock_entry_type, you need to set a custom query for the reference_document field
frappe.ui.form.on("Delivery Note Trip Sheet", {
  reference_doctype: function (frm, cdt, cdn) {
    var child = locals[cdt][cdn];
    if (child.reference_doctype === "Stock Entry") {
      frappe.meta.get_docfield(
        "Delivery Note Trip Sheet",
        "reference_document",
        frm.doc.name
      ).get_query = function () {
        return {
          filters: {
            stock_entry_type: "Material Issue",
          },
        };
      };
    } else {
      frappe.meta.get_docfield(
        "Delivery Note Trip Sheet",
        "reference_document",
        frm.doc.name
      ).get_query = null;
    }
  },

  // Optionally, trigger fetch_reference_items on delivery_note table change
  reference_document: function (frm, cdt, cdn) {
    frm.trigger("fetch_reference_items");
  },
});
