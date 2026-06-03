frappe.ui.form.SelectDialog = Class.extend({
    init: function (opts) {
        $.extend(this, opts);
        var me = this;
        this.make();
    },
    make: function () {
        let me = this;

        this.page_length = 20;
        this.start = 0;
        let fields = [];
        let count = 0;
        if (!this.date_field) {
            this.date_field = "transaction_date";
        }


        if ($.isArray(this.query_fields)) {
            for (let df of this.query_fields) {
                if (df.filter) {
                    fields.push(df, { fieldtype: "Column Break" });
                }
            }
        }

        fields = fields.concat([
            {
                "fieldname": "date_range",
                "label": __("Date Range"),
                "fieldtype": "DateRange",
            },
            { fieldtype: "Section Break" },
            { fieldtype: "HTML", fieldname: "results_area" },
            {
                fieldtype: "Button", fieldname: "more_btn", label: __("More"),
                click: function () {
                    me.start += 20;
                    frappe.flags.auto_scroll = true;
                    me.get_results();
                }
            }
        ]);

        this.dialog = new frappe.ui.Dialog({
            title: __(this.title),
            fields: fields,
            primary_action_label: __("Select"),
            primary_action: function () {
                me.action(me.get_checked_values(), me.args);
                cur_dialog.hide();
            },
        });

        this.$parent = $(this.dialog.body);
        this.$wrapper = this.dialog.fields_dict.results_area.$wrapper.append(`<div class="results"
			style="border: 1px solid #d1d8dd; border-radius: 3px; height: 300px; overflow: auto;"></div>`);

        this.$results = this.$wrapper.find('.results');
        this.$results.append(this.make_list_row());

        this.args = {};

        this.bind_events();
        this.get_results();
        this.dialog.show();
    },

    bind_events: function () {
        let me = this;

        this.$results.on('click', '.list-item-container', function (e) {
            if (!$(e.target).is(':checkbox') && !$(e.target).is('a')) {
                $(this).find(':checkbox').trigger('click');

            }
        });
        this.$results.on('click', '.list-item--head :checkbox', (e) => {
            this.$results.find('.list-item-container .list-row-check')
                .prop("checked", ($(e.target).is(':checked')));
        });

        this.$parent.find('.input-with-feedback').on('change', (e) => {
            frappe.flags.auto_scroll = false;
            this.get_results();

        });


        this.$parent.find('[data-fieldname="date_range"]').on('blur', (e) => {
            frappe.flags.auto_scroll = false;
            this.get_results();
        });


    },

    get_checked_values: function () {
        var me = this;
        return this.$results.find('.list-item-container').map(function () {
            if ($(this).find('.list-row-check:checkbox:checked').length > 0) {
                return $(this).find(`[data-item-${me.return_field}]`).attr(`data-item-${me.return_field}`);
            }
        }).get();
    },

    make_list_row: function (result = {}) {
        var me = this;
        // Make a head row by default (if result not passed)
        let head = Object.keys(result).length === 0;

        let contents = ``;
        let columns = [];

        if ($.isArray(this.query_fields)) {
            for (let df of this.query_fields) {
                columns.push(df.fieldname);
            }
        }
        columns.push("Date");

        columns.forEach(function (column) {
            contents += `<div class="list-item__content ellipsis">
				${head ? `<span class="ellipsis">${__(frappe.model.unscrub(column))}</span>`
                    : `<span class="ellipsis" data-item-${column}="${result[column]}">${__(result[column])}</span>`
                }
			</div>`;
        });

        let $row = $(`<div class="list-item">
			<div class="list-item__content" style="flex: 0 0 10px;">
				<input type="checkbox" class="list-row-check" data-item-name="${result.name}" ${result.checked ? 'checked' : ''}>
			</div>
			${contents}
		</div>`);


        head ? $row.addClass('list-item--head')
            : $row = $(`<div class="list-item-container" data-item-name="${result.name}"></div>`).append($row);
        if (!me.multi_select) {
            $(".results").find('.list-row-check').on('change', function () {
                $('input.list-row-check').not(this).prop('checked', false);
            });
        }

        return $row;
    },

    render_result_list: function (results, more = 0) {
        var me = this;
        var more_btn = me.dialog.fields_dict.more_btn.$wrapper;

        // Make empty result set if filter is set
        if (!frappe.flags.auto_scroll) {
            this.empty_list();
        }
        more_btn.hide();

        if (results.length === 0) return;
        if (more && me.page_length + me.start < results.length) {
            more_btn.show();
        } else { more_btn.hide(); }
        $(".results").find(".list-item-container").remove();
        results.forEach((result) => {
            me.$results.append(me.make_list_row(result));
        });

        if (frappe.flags.auto_scroll) {
            this.$results.animate({ scrollTop: me.$results.prop('scrollHeight') }, 500);
        }
    },

    empty_list: function () {
        this.$results.find('.list-item-container').remove();
    },

    get_results: function () {
        let me = this;

        let filters = this.get_query ? this.get_query().filters : {};
        let filter_fields = [me.date_field];
        if ($.isArray(this.query_fields)) {
            for (let df of this.query_fields) {
                if (df.filter) {
                    filters[df.fieldname] = me.dialog.fields_dict[df.fieldname].get_value() || undefined;
                    me.args[df.fieldname] = filters[df.fieldname];
                    filter_fields.push(df.fieldname);
                }

            }
        }

        let date_val = this.dialog.fields_dict["date_range"].get_value();
        if (date_val) {
            filters[this.date_field] = ['between', date_val];
        }

        let args = {
            doctype: "",
            txt: "",
            filters: filters,
            filter_fields: filter_fields,
            start: this.start,
            page_length: this.page_length + 1,
            query: this.get_query ? this.get_query().query : '',
            as_dict: 1
        };
        frappe.call({
            type: "GET",
            method: 'frappe.desk.search.search_widget',
            no_spinner: true,
            args: args,
            callback: function (r) {
                if (r.message) { r.values = r.message; }
                let results = [], more = 0;
                if (r.values.length) {
                    if (r.values.length > me.page_length) {
                        r.values.pop();
                        more = 1;
                    }
                    r.values.forEach(function (result) {
                        if (me.date_field in result) {
                            result["Date"] = result[me.date_field];
                        }
                        result.checked = 0;
                        result.parsed_date = Date.parse(result["Date"]);
                        results.push(result);
                    });
                    results.map((result) => {
                        result["Date"] = frappe.format(result["Date"], { "fieldtype": "Date" });
                    });

                    results.sort((a, b) => {
                        return a.parsed_date - b.parsed_date;
                    });

                    // Preselect oldest entry
                    if (me.start < 1 && r.values.length === 1) {
                        results[0].checked = 1;
                    }
                }
                else {
                    frappe.show_alert({ message: __('There is No Records'), indicator: 'red' }, 5);
                }
                me.render_result_list(results, more);
            }
        });
    },
});
