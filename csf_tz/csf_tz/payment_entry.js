frappe.ui.form.on("Payment Entry", {
	onload: function (frm) {
		if (frm.is_new()) {
			frm.trigger("payment_type");
		}
	},
	refresh: function (frm) {
		frm.trigger("add_write_off_button");
	},
	payment_type: function (frm) {
		if (frm.is_new()) {
			if (frm.doc.payment_type == "Receive") {
				frm.set_value("naming_series", "RE-.YYYY.-");
				if (!["Student", "Donor"].includes(frm.doc.party_type)) {
					frm.set_value("party_type", "Customer");
				}
			}
			else if (frm.doc.payment_type == "Pay") {
				frm.set_value("naming_series", "PE-.YYYY.-");
				if (frm.doc.party_type != "Employee") {
					frm.set_value("party_type", "Supplier");
				}
			}
			else if (frm.doc.payment_type == "Internal Transfer") {
				frm.set_value("naming_series", "IT-.YYYY.-");
				frm.set_value("party_type", "");
				frm.set_value("party_name", "");
			}
		}
		frm.refresh_fields()
	},

	party: function (frm) {
		if (frm.is_new()) {
			// check if the feature is disabled in CSF TZ Settings
			frappe.db.get_single_value("CSF TZ Settings", "disable_get_outstanding_functionality")
			.then(disabled => {
				if (disabled) {
					// Feature is disabled, do not proceed with get_outstanding_documents
					return;
				}
				
				// Feature is enabled, proceed with existing functionality
			const today = frappe.datetime.get_today();
			const filters = {
				from_posting_date: frappe.datetime.add_days(today, -3650),
				to_posting_date: today,
				allocate_payment_amount: 1
			}
			if (["Customer", "Supplier"].includes(frm.doc.party_type) && frm.doc.paid_from_account_currency && frm.doc.paid_to_account_currency) {
				frm.events.get_outstanding_documents(frm, filters);
			  }
		    });
		}
	},

	get_outstanding_documents: function (frm, filters) {
		// first check if the feature s disabled in CSF TZ Settings
		return frappe.db.get_single_value("CSF TZ Settings", "disable_get_outstanding_functionality")
			.then(disabled => {
				if (disabled) {
					// Feature is disabled, do not proceed
					return;
				}
				
				// Continue with normal functionality
		if (typeof frappe.route_history[frappe.route_history.length - 2] != "undefined") {
			if (frappe.route_history[frappe.route_history.length - 2][1] in ["Sales Invoice", "Employee Advance", "Purchase Invoice"]) {
				return;
			}
		}

		frm.clear_table("references");

		if (!frm.doc.party) {
			return;
		}

		frm.events.check_mandatory_to_fetch(frm);

		// Ensure party account is set based on payment type
		var party_account = frm.doc.payment_type == "Receive" ? frm.doc.paid_from : frm.doc.paid_to;
		if (!party_account) {
			frappe.msgprint(__("Please set the appropriate account for the selected payment type."));
			return;
		}

		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;

		var args = {
			"posting_date": frm.doc.posting_date,
			"company": frm.doc.company,
			"party_type": frm.doc.party_type,
			"payment_type": frm.doc.payment_type,
			"party": frm.doc.party,
			"party_account": party_account,
			"cost_center": frm.doc.cost_center
		}

		for (let key in filters) {
			args[key] = filters[key];
		}

		frappe.flags.allocate_payment_amount = filters['allocate_payment_amount'];


		return frappe.call({
			method: 'csf_tz.csftz_hooks.payment_entry.get_outstanding_reference_documents',
			args: {
				args: args
			},
			callback: function (r, rt) {
				if (r.message) {
					var total_positive_outstanding = 0;
					var total_negative_outstanding = 0;

					$.each(r.message, function (i, d) {
						var c = frm.add_child("references");
						c.reference_doctype = d.voucher_type;
						c.reference_name = d.voucher_no;
						c.due_date = d.due_date;
						c.posting_date = d.posting_date;
						c.total_amount = d.invoice_amount;
						c.outstanding_amount = d.outstanding_amount;
						c.bill_no = d.bill_no;

						if (!in_list(["Sales Order", "Purchase Order", "Expense Claim", "Fees"], d.voucher_type)) {
							if (flt(d.outstanding_amount) > 0)
								total_positive_outstanding += flt(d.outstanding_amount);
							else
								total_negative_outstanding += Math.abs(flt(d.outstanding_amount));
						}

						var party_account_currency = frm.doc.payment_type == "Receive" ?
							frm.doc.paid_from_account_currency : frm.doc.paid_to_account_currency;

						if (party_account_currency != company_currency) {
							c.exchange_rate = d.exchange_rate;
						} else {
							c.exchange_rate = 1;
						}
						if (in_list(['Sales Invoice', 'Purchase Invoice', "Expense Claim", "Fees"], d.reference_doctype)) {
							c.due_date = d.due_date;
						}
					});

					if (
						(frm.doc.payment_type == "Receive" && frm.doc.party_type == "Customer") ||
						(frm.doc.payment_type == "Pay" && frm.doc.party_type == "Supplier") ||
						(frm.doc.payment_type == "Pay" && frm.doc.party_type == "Employee") ||
						(frm.doc.payment_type == "Receive" && frm.doc.party_type == "Student")
					) {
						if (total_positive_outstanding > total_negative_outstanding)
							if (!frm.doc.paid_amount)
								frm.set_value("paid_amount",
									total_positive_outstanding - total_negative_outstanding);
					} else if (
						total_negative_outstanding &&
						total_positive_outstanding < total_negative_outstanding
					) {
						if (!frm.doc.received_amount)
							frm.set_value("received_amount",
								total_negative_outstanding - total_positive_outstanding);
					}
				}

				const paid_amount = frm.doc.payment_type == "Receive" ? frm.doc.paid_amount : frm.doc.received_amount;
				if (paid_amount) {
					frm.events.allocate_party_amount_against_ref_docs(frm, paid_amount, true);
				}

			}
		  });
		});
	},
	get_outstanding_so: function (frm) {
		const today = frappe.datetime.get_today();
		let fields = [
			{ fieldtype: "Section Break", label: __("Posting Date") },
			{
				fieldtype: "Date",
				label: __("From Date"),
				fieldname: "from_posting_date",
				default: frappe.datetime.add_days(today, -30),
			},
			{ fieldtype: "Column Break" },
			{ fieldtype: "Date", label: __("To Date"), fieldname: "to_posting_date", default: today },
			{ fieldtype: "Section Break", label: __("Due Date") },
			{ fieldtype: "Date", label: __("From Date"), fieldname: "from_due_date" },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Date", label: __("To Date"), fieldname: "to_due_date" },
			{ fieldtype: "Section Break", label: __("Outstanding Amount") },
			{
				fieldtype: "Float",
				label: __("Greater Than Amount"),
				fieldname: "outstanding_amt_greater_than",
				default: 0,
			},
			{ fieldtype: "Column Break" },
			{ fieldtype: "Float", label: __("Less Than Amount"), fieldname: "outstanding_amt_less_than" },
			{ 
				fieldtype: "Check",
				label: __("Allocate Payment Amount"),
				fieldname: "allocate_payment_amount",
				default: 1
			}
		];

		frappe.prompt(
			fields,
			function (filters) {
				frm.clear_table("references");
				
				if (!frm.doc.party) {
					frappe.throw(__("Please select a Party first"));
					return;
				}

				frm.events.check_mandatory_to_fetch(frm);

				// Ensure party account is set based on payment type
				var party_account = frm.doc.payment_type == "Receive" ? frm.doc.paid_from : frm.doc.paid_to;
				if (!party_account) {
					frappe.msgprint(__("Please set the appropriate account for the selected payment type."));
					return;
				}

				frappe.flags.allocate_payment_amount = filters.allocate_payment_amount;
				
				var args = {
					"posting_date": frm.doc.posting_date,
					"company": frm.doc.company,
					"party_type": frm.doc.party_type,
					"payment_type": frm.doc.payment_type,
					"party": frm.doc.party,
					"party_account": party_account,
					"cost_center": frm.doc.cost_center,
					"from_posting_date": filters.from_posting_date,
					"to_posting_date": filters.to_posting_date,
					"from_due_date": filters.from_due_date,
					"to_due_date": filters.to_due_date,
					"outstanding_amt_greater_than": filters.outstanding_amt_greater_than,
					"outstanding_amt_less_than": filters.outstanding_amt_less_than,
					"allocate_payment_amount": filters.allocate_payment_amount
				};

				return frappe.call({
					method: 'csf_tz.csftz_hooks.payment_entry.get_outstanding_sales_orders',
					args: {
						args: args
					},
					callback: function (r, rt) {
						if (r.message) {
							var total_positive_outstanding = 0;

							$.each(r.message, function (i, d) {
								var c = frm.add_child("references");
								c.reference_doctype = d.voucher_type;
								c.reference_name = d.voucher_no;
								c.due_date = d.due_date;
								c.posting_date = d.posting_date;
								c.total_amount = d.invoice_amount;
								c.outstanding_amount = d.outstanding_amount;
								
								// Add to total outstanding
								total_positive_outstanding += flt(d.outstanding_amount);
								
								var party_account_currency = frm.doc.payment_type == "Receive" ?
									frm.doc.paid_from_account_currency : frm.doc.paid_to_account_currency;
								
								var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
								
								if (party_account_currency != company_currency) {
									c.exchange_rate = d.exchange_rate;
								} else {
									c.exchange_rate = 1;
								}
							});

							// Set paid amount based on outstanding sales orders
							if (total_positive_outstanding > 0 && frappe.flags.allocate_payment_amount) {
								if (frm.doc.payment_type == "Receive" && !frm.doc.paid_amount) {
									frm.set_value("paid_amount", total_positive_outstanding);
								} else if (frm.doc.payment_type == "Pay" && !frm.doc.received_amount) {
									frm.set_value("received_amount", total_positive_outstanding);
								}
							}
							
							frm.refresh_fields();
							
							const paid_amount = frm.doc.payment_type == "Receive" ? frm.doc.paid_amount : frm.doc.received_amount;
							if (paid_amount && frappe.flags.allocate_payment_amount) {
								frm.events.allocate_party_amount_against_ref_docs(frm, paid_amount, true);
							}
						}
					}
				});
			},
			__("Filters"),
			__("Get Sales Orders")
		);
	},

	// Write-off Journal Entry Feature
	add_write_off_button: function (frm) {
		// Check if feature is enabled and conditions are met
		frappe.db
			.get_single_value("CSF TZ Settings", "enable_write_off_jv_si")
			.then((enable_write_off) => {
				if (enable_write_off &&
					frm.doc.docstatus === 1 &&
					frm.doc.unallocated_amount > 0) {

					frm.add_custom_button(__("Write Off Outstanding"), function () {
						// Fetch the write-off account from Company before showing the dialog
						frappe.db.get_value("Company", frm.doc.company, "write_off_account").then(function(r) {
							let write_off_account = r.message ? r.message.write_off_account : null;

							// Show dialog to select write-off account
							let dialog = new frappe.ui.Dialog({
								title: __("Write Off Unallocated Amount"),
								fields: [
									{
										fieldname: "write_off_account",
										label: __("Write Off Account"),
										fieldtype: "Link",
										options: "Account",
										"default": write_off_account,
										reqd: 1,
										get_query: function() {
											return {
												filters: {
													"report_type": "Balance Sheet",
													"is_group": 0,
													"company": frm.doc.company
												}
											};
										}
									},
									{
										fieldname: "unallocated_amount",
										label: __("Unallocated Amount"),
										fieldtype: "Currency",
										default: frm.doc.unallocated_amount,
										read_only: 1
									}
								],
								primary_action_label: __("Create Write Off Entry"),
								primary_action: function(values) {
									frappe.call({
										method: "csf_tz.custom_api.create_write_off_jv_pe",
										args: {
											payment_entry: frm.doc.name,
											account: values.write_off_account
										},
										callback: function(r) {
											if (r.message) {
												frappe.msgprint(__("Write-off Journal Entry created: {0}", [r.message]));
												frm.reload_doc();
											}
										}
									});
									dialog.hide();
								}
							});
							dialog.show();
						});
					}, __("Create"));
				}
			});
	}
});
