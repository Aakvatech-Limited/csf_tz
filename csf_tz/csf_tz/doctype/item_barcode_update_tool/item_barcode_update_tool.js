// Copyright (c) 2022, Aakvatech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item Barcode Update Tool', {
	'item_code': function (frm, cdt, cdn) {
		var doc = locals[cdt][cdn];
		if (doc.item_code) {
			frappe.call({
				method: "frappe.client.get",
				args: {
					name: doc.item_code,
					doctype: "Item"
				},
				callback(r) {
					// console.log(r);
					if (r.message) {
						for (var row in r.message.barcodes) {
							var child = frm.add_child("barcodes");
							frappe.model.set_value(child.doctype, child.name, "barcode", r.message.barcodes[row].barcode);
							frappe.model.set_value(child.doctype, child.name, "barcode_type", r.message.barcodes[row].barcode_type);
							frappe.model.set_value(child.doctype, child.name, "uom", r.message.barcodes[row].uom);
							refresh_field("barcodes");
						}
					}
				}
			})
		}
	},
	refresh(frm) {
		$(".btn-primary").hide()
	},
	'update_barcodes': function (frm) {
		frappe.call({
			method: "csf_tz.csf_tz.doctype.item_barcode_update_tool.item_barcode_update_tool.update_barcodes",
			args: {
				doc: frm.doc
			},
			callback: function (r) {
				// frappe.msgprint(__("Barcodes updated successfully for Item " + frm.doc.item_name))
				return
			}
		});
	},
})
