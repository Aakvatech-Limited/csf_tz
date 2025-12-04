frappe.require([
    '/assets/csf_tz/js/shortcuts.js'
]);

// Budget check for Material Request is now handled server-side via doc_events hooks
// See apps/csf_tz/csf_tz/hooks.py and apps/csf_tz/csf_tz/budget_check.py

frappe.ui.form.on('Material Request', {
    // Client-side validate event removed - budget check now runs server-side
});

frappe.ui.keys.add_shortcut({
    shortcut: 'ctrl+q',
    action: () => {
        ctrlQ("Material Request Item");
    },
    page: this.page,
    description: __('Select Item Warehouse'),
    ignore_inputs: true,
});