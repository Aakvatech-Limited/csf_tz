frappe.ui.form.on('Stock Reconciliation', {
	sort_items: function (frm, cdt, cdn) {
        const sorted_list =frm.doc.items.sort((a,b) => (a.item_code > b.item_code) ? 1 : -1);
        sorted_list.forEach((i,idx) => {
            const row = locals["Stock Reconciliation Item"][i.name];
            row.idx = idx + 1;
        });
        refresh_field("items");
	},

})
