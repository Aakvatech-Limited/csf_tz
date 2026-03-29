// Hook into the specific form or field where you want to override the behavior
frappe.ui.form.ControlLink = class CustomControlLink extends frappe.ui.form.ControlLink {

    // Override the setup_awesomeplete method specifically
    setup_awesomeplete() {
        let me = this;

        this.$input.cache = {};

        // Initialize Awesomplete
        this.awesomplete = new Awesomplete(me.input, {
            minChars: 0,
            maxItems: 99,
            autoFirst: true,
            list: [],
            replace: function (item) {
                this.input.value = me.get_translated(item.label || item.value);
            },
            data: function (item) {
                return {
                    label: me.get_translated(item.label || item.value),
                    value: item.value,
                };
            },
            filter: function () {
                return true;
            },
            item: function (item) {
                let d = this.get_item(item.value);
                if (!d.label) {
                    d.label = d.value;
                }

                let _label = me.get_translated(d.label);
                let html = d.html || "<strong>" + _label + "</strong>";
                if (d.description && (me.is_title_link() || d.value !== d.description)) {
                    html += '<br><span class="small">' + __(d.description) + "</span>";
                }
                return $("<li></li>")
                    .data("item.autocomplete", d)
                    .prop("aria-selected", "false")
                    .html(`<a><p title="${frappe.utils.escape_html(_label)}">${html}</p></a>`)
                    .get(0);
            },
            sort: function () {
                return 0;
            },
        });

        // Custom filter logic applied dynamically
        this.$input.on(
            "input",
            frappe.utils.debounce(function (e) {
                var doctype = me.get_options();
                if (!doctype) return;
                if (!me.$input.cache[doctype]) {
                    me.$input.cache[doctype] = {};
                }

                var term = e.target.value;

                if (me.$input.cache[doctype][term] != null) {
                    me.awesomplete.list = me.$input.cache[doctype][term];
                }

                // Fetch filters dynamically from the whitelisted method
                frappe.call({
                    method: "csf_tz.csftz_hooks.custom_search_link.get_custom_filters",  // Whitelisted method to fetch filters
                    args: {
                        reference_doctype: me.get_reference_doctype() || "",
                    },
                    callback: function (r) {
                        let filters = [];

                        // Check if filters are returned, otherwise continue without filters
                        if (r.message && r.message.length > 0) {
                            filters = r.message;
                        }

                        var args = {
                            txt: term,
                            doctype: doctype,
                            filters: filters,  // Use the dynamically fetched filters (if any)
                            ignore_user_permissions: me.df.ignore_user_permissions,
                            reference_doctype: me.get_reference_doctype() || "",
                        };

                        // Perform the server call to fetch the filtered results
                        frappe.call({
                            type: "POST",
                            method: "frappe.desk.search.search_link",
                            no_spinner: true,
                            args: args,
                            callback: function (r) {
                                if (!window.Cypress && !me.$input.is(":focus")) {
                                    return;
                                }

                                r.results = me.merge_duplicates(r.results);

                                if (args.filters && args.filters.length > 0) {
                                    let filter_string = me.get_filter_description(args.filters);
                                    if (filter_string) {
                                        r.results.push({
                                            html: `<span class="text-muted" style="line-height: 1.5">${filter_string}</span>`,
                                            value: "",
                                            action: () => { },
                                        });
                                    }
                                }

                                // Handle "Create New" button and Advanced Search
                                if (!me.df.only_select) {
                                    if (frappe.model.can_create(doctype)) {
                                        r.results.push({
                                            html:
                                                "<span class='text-primary link-option'>" +
                                                "<i class='fa fa-plus' style='margin-right: 5px;'></i> " +
                                                __("Create a new {0}", [__(me.get_options())]) +
                                                "</span>",
                                            label: __("Create a new {0}", [__(me.get_options())]),
                                            value: "create_new__link_option",
                                            action: me.new_doc,
                                        });
                                    }

                                    // Custom link actions (if any)
                                    let custom__link_options =
                                        frappe.ui.form.ControlLink.link_options &&
                                        frappe.ui.form.ControlLink.link_options(me);

                                    if (custom__link_options) {
                                        r.results = r.results.concat(custom__link_options);
                                    }

                                    if (locals && locals["DocType"]) {
                                        r.results.push({
                                            html:
                                                "<span class='text-primary link-option'>" +
                                                "<i class='fa fa-search' style='margin-right: 5px;'></i> " +
                                                __("Advanced Search") +
                                                "</span>",
                                            label: __("Advanced Search"),
                                            value: "advanced_search__link_option",
                                            action: me.open_advanced_search,
                                        });
                                    }
                                }

                                me.$input.cache[doctype][term] = r.results;
                                me.awesomplete.list = me.$input.cache[doctype][term];
                                me.toggle_href(doctype);
                            },
                        });
                    },
                });
            }, 500)
        );

        // Handle input blur events
        this.$input.on("blur", function () {
            if (me.selected) {
                me.selected = false;
                return;
            }
            let value = me.get_input_value();
            let label = me.get_label_value();
            let last_value = me.last_value || "";
            let last_label = me.label || "";

            if (value !== last_value) {
                me.parse_validate_and_set_in_model(value, null, label);
            }
        });

        // Awesomplete open/close events
        this.$input.on("awesomplete-open", () => {
            this.autocomplete_open = true;

            if (!me.get_label_value()) {
                me.$link.toggle(false);
            }
        });

        this.$input.on("awesomplete-close", (e) => {
            this.autocomplete_open = false;

            if (!me.get_label_value()) {
                me.$link.toggle(false);
            }
        });

        this.$input.on("awesomplete-select", function (e) {
            var o = e.originalEvent;
            var item = me.awesomplete.get_item(o.text.value);

            me.autocomplete_open = false;

            let TABKEY = 9;
            if (e.keyCode === TABKEY) {
                e.preventDefault();
                me.awesomplete.close();
                return false;
            }

            if (item.action) {
                item.value = "";
                item.label = "";
                item.action.apply(me);
            }

            if (me.df.remember_last_selected_value) {
                frappe.boot.user.last_selected_values[me.df.options] = item.value;
            }

            me.parse_validate_and_set_in_model(item.value, null, item.label);
        });

        this.$input.on("awesomplete-selectcomplete", function (e) {
            let o = e.originalEvent;
            if (o.text.value.indexOf("__link_option") !== -1) {
                me.$input.val("");
            }
        });
    }
};
