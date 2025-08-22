// List view controller
frappe.listview_settings['Workflow Transition History'] = {
    get_indicator: function(doc) {
        const color_map = {
            'Draft': 'blue',
            'Submitted': 'green',
            'Cancelled': 'red',
            'Approved': 'green',
            'Rejected': 'red'
        };
        
        const color = color_map[doc.current_state] || 'orange';
        return [__(doc.current_state), color, 'current_state,=,' + doc.current_state];
    },
    
    onload: function(listview) {
        // Add custom filter button
        listview.page.add_menu_item(__("Filter by Workflow"), function() {
            const dialog = new frappe.ui.Dialog({
                title: __('Filter by Workflow'),
                fields: [
                    {
                        label: __('Workflow'),
                        fieldname: 'workflow',
                        fieldtype: 'Link',
                        options: 'Workflow'
                    },
                    {
                        label: __('Status'),
                        fieldname: 'status',
                        fieldtype: 'Select',
                        options: ['All', 'Draft', 'Submitted', 'Cancelled', 'Approved', 'Rejected']
                    }
                ],
                primary_action: function(values) {
                    const filters = [];
                    
                    if(values.workflow) {
                        filters.push(['Workflow Transition History', 'workflow', '=', values.workflow]);
                    }
                    
                    if(values.status && values.status !== 'All') {
                        filters.push(['Workflow Transition History', 'current_state', '=', values.status]);
                    }
                    
                    listview.filter_area.add(filters);
                    listview.run();
                    dialog.hide();
                }
            });
            
            dialog.show();
        });
    },
    
    formatters: {
        user: function(value) {
            return frappe.user.full_name(value);
        },
        transition_date: function(value) {
            return frappe.datetime.global_date_format(value);
        }
    }
};