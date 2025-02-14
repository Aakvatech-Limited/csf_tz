frappe.listview_settings['Custom Field'] = {
    onload: function (listview) {
        listview.page.add_menu_item(__('Export Selected'), async function () {
            const selected_docs = listview.get_checked_items();
            if (selected_docs.length === 0) {
                frappe.msgprint(__('Please select at least one document.'));
                return;
            }

            const detailed_docs = await Promise.all(selected_docs.map(doc =>
                fetch(`/api/resource/Custom Field/${doc.name}`)
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
                    dt: doc.dt,
                    label: doc.label,
                    fieldname: doc.fieldname,
                    insert_after: doc.insert_after,
                    length: doc.length,
                    fieldtype: doc.fieldtype,
                    precision: doc.precision,
                    hide_seconds: doc.hide_seconds,
                    hide_days: doc.hide_days,
                    options: doc.options,
                    sort_options: doc.sort_options,
                    fetch_if_empty: doc.fetch_if_empty, 
                    fetch_from: doc.fetch_from,
                    collapsible: doc.collapsible,
                    non_negative: doc.non_negative,
                    mandatory_depends_on: doc.mandatory_depends_on,
                    depends_on: doc.depends_on,
                    reqd: doc.reqd,
                    unique: doc.unique,
                    is_virtual: doc.is_virtual,
                    read_only: doc.read_only,
                    ignore_user_permissions: doc.ignore_user_permissions,
                    hidden: doc.hidden,
                    print_hide: doc.print_hide,
                    print_hide_if_no_value: doc.print_hide_if_no_value,
                    no_copy: doc.no_copy,
                    allow_on_submit: doc.allow_on_submit,
                    in_list_view: doc.in_list_view,
                    in_standard_filter: doc.in_standard_filter,
                    in_global_search: doc.in_global_search,
                    in_preview: doc.in_preview,
                    bold: doc.bold,
                    report_hide: doc.report_hide,
                    search_index: doc.search_index,
                    allow_in_quick_entry: doc.allow_in_quick_entry,
                    ignore_xss_filter: doc.ignore_xss_filter,
                    translatable: doc.translatable,
                    hide_border: doc.hide_border,
                    show_dashboard: doc.show_dashboard,
                    permlevel: doc.permlevel,
                    columns: doc.columns,
                    doctype: doc.doctype,
                    __last_sync_on: doc.__last_sync_on
                };
            });

            const jsonStr = JSON.stringify(data_to_export);
            let blob = new Blob([jsonStr], { type: "application/json" });
            let a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = "exported_custom_fields.json";
            a.click();
            URL.revokeObjectURL(a.href);
            a.remove();
        });
    }
};