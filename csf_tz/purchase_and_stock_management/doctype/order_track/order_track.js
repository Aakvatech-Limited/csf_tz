// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Order Track', {

	refresh: function(frm) {
        frm.events.show_hide_fields(frm);
        console.log(frm);
        //console.log(hide_show_sections.name);
        //alert(cur_frm.doc.docstatus)

        //make product inspection ie. submitted
         if(cur_frm.doc.docstatus === 1 ) {
		      cur_frm.add_custom_button(__('Product Inspection'), function(){frm.events.make_product_inspection(frm)}, __("Make"));


        }



         //Arrival date entered,clearing company and completion date ! blank
		if (frm.doc.arrival_date && frm.doc.arrival_date != null ){
		   if (frm.doc.clearing_company == '' || (frm.doc.expected_clearing_completion_date ==null)){
			var msg = "Either Clearing Company or Clearing Completion Date is unfilled,Please fill the fields";
			frappe.msgprint(msg);
			throw msg;

			}
		}
	},


	show_hide_fields:function(frm){
       frm.toggle_display('section_international_supplier',(frm.doc.supplier && frm.doc.supplier_type && frm.doc.supplier_type=='International Supplier' ));
       frm.toggle_display('section_containers',(frm.doc.supplier && frm.doc.supplier_type && frm.doc.supplier_type=='International Supplier'));
       frm.toggle_display('section_local_supplier', (frm.doc.supplier && frm.doc.supplier_type && frm.doc.supplier_type=='Local Supplier'));
       frm.toggle_display('section_order_progress',(frm.doc.supplier  && frm.doc.supplier_type));
       frm.toggle_display('section_items_ordered', (frm.doc.supplier && frm.doc.supplier_type));
       frm.toggle_display('section_status', (frm.doc.supplier && frm.doc.supplier_type));
    },



    supplier:function(frm){
        frm.events.show_hide_fields(frm);

    },

    supplier_type:function(frm){
     frm.events.show_hide_fields(frm);
    },

          //Product Inspection function
    make_product_inspection:function(){
        frappe.model.open_mapped_doc({
			method: "erpnext.purchase_and_stock_management.doctype.order_track.order_track.make_product_inspection",
			frm: cur_frm
		})

    },

});
