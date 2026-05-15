frappe.listview_settings['Property Setter'] = {
    onload: function (listview) {
        listview.page.add_menu_item(__('Export Selected'), async function () {
            const selected_docs = listview.get_checked_items();
            if (selected_docs.length === 0) {
                frappe.msgprint(__('Please select at least one document.'));
                return;
            }

            const detailed_docs = await Promise.all(selected_docs.map(doc =>
                fetch(`/api/resource/Property Setter/${doc.name}`)
                    .then(response => response.json())
                    .then(data => data.data)
            ));

            const data_to_export = detailed_docs.map(doc => {
                return {
                    name: doc.name,
                    owner: doc.owner,
                    creation: doc.creation,
                    modified: doc.modified,
                    modified_by: doc.modified_by,
                    docstatus: doc.docstatus,
                    idx: doc.idx,
                    is_system_generated: doc.is_system_generated,
                    doctype_or_field: doc.doctype_or_field,
                    doc_type: doc.doc_type,
                    field_name: doc.field_name,
                    property: doc.property,
                    property_type: doc.property_type,
                    value: doc.value,
                    doctype: doc.doctype,
                    __last_sync_on: doc.__last_sync_on
                };
            });

            const jsonStr = JSON.stringify(data_to_export);
            let blob = new Blob([jsonStr], { type: "application/json" });
            let a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = "exported_property_setters.json";
            a.click();
            URL.revokeObjectURL(a.href);
            a.remove();
        });
    }
};
