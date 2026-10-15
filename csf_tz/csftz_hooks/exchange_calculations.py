import frappe
from frappe import _
from frappe.utils import flt, nowdate


def create_import_tracker(doc, method):
	"""Create Foreign Import Transaction when Purchase Invoice is submitted"""
	if not doc.currency:
		return

	company_currency = frappe.get_cached_value("Company", doc.company, "default_currency")

	# Only create tracker for foreign currency invoices
	if doc.currency == company_currency:
		return

	# Check if tracker already exists
	existing = frappe.db.exists("Foreign Import Transaction", {"purchase_invoice": doc.name})
	if existing:
		return

	try:
		import_tracker = frappe.new_doc("Foreign Import Transaction")
		import_tracker.purchase_invoice = doc.name
		import_tracker.supplier = doc.supplier
		import_tracker.transaction_date = doc.posting_date
		import_tracker.currency = doc.currency
		import_tracker.original_exchange_rate = doc.conversion_rate
		import_tracker.invoice_amount_foreign = doc.grand_total
		import_tracker.invoice_amount_base = doc.base_grand_total
		import_tracker.company = doc.company
		import_tracker.status = "Draft"

		import_tracker.insert()
		import_tracker.submit()

		doc.db_set("foreign_import_tracker", import_tracker.name)

		frappe.msgprint(
			_("Foreign Import Transaction {0} created successfully").format(import_tracker.name),
			alert=True,
		)

	except Exception as e:
		frappe.log_error(f"Error creating Foreign Import Transaction for {doc.name}: {str(e)}")


def cancel_import_tracker(doc, method):
	"""Cancel Foreign Import Transaction when Purchase Invoice is cancelled"""
	tracker_name = frappe.db.get_value("Foreign Import Transaction", {"purchase_invoice": doc.name}, "name")

	if tracker_name:
		try:
			tracker = frappe.get_doc("Foreign Import Transaction", tracker_name)
			if tracker.docstatus == 1:
				tracker.cancel()
		except Exception as e:
			frappe.log_error(
				"Error on Cancelling Foreign Import Transaction",
				f"Error cancelling Foreign Import Transaction {tracker_name}: {str(e)}",
			)


def link_lcv_to_import_tracker(doc, method):
	"""Link Landed Cost Voucher to Foreign Import Transaction"""
	if not doc.purchase_receipts:
		return

	for pr_row in doc.purchase_receipts:
		receipt_doc = pr_row.get("receipt_document") or pr_row.get("purchase_receipt")
		if not receipt_doc:
			continue

		# Find related purchase invoice through purchase receipt
		if pr_row.get("receipt_document_type") == "Purchase Invoice":
			pi_items = [{"purchase_invoice": receipt_doc}]
		else:
			pi_item = frappe.qb.DocType("Purchase Invoice Item")
			pi_items = (
				frappe.qb.from_(pi_item)
				.select(pi_item.parent.as_("purchase_invoice"))
				.distinct()
				.where(pi_item.purchase_receipt == receipt_doc)
				.run(as_dict=True)
			)

		for pi_item in pi_items:
			purchase_invoice = pi_item.get("purchase_invoice")
			if not purchase_invoice:
				continue
			tracker_name = frappe.db.get_value(
				"Foreign Import Transaction",
				{"purchase_invoice": purchase_invoice},
				"name",
			)

			if tracker_name:
				try:
					tracker_doc = frappe.get_doc("Foreign Import Transaction", tracker_name)

					# Check if LCV already added
					existing_lcv = any(
						row.landed_cost_voucher == doc.name for row in tracker_doc.landed_cost_vouchers
					)
					if not existing_lcv:
						tracker_doc.add_lcv_detail(doc.name)

						# Calculate LCV exchange difference
						calculate_lcv_exchange_difference(tracker_doc, doc)

				except Exception as e:
					frappe.log_error(f"Error linking LCV {doc.name} to tracker {tracker_name}: {str(e)}")


def unlink_lcv_from_import_tracker(doc, method):
	"""Remove LCV from Foreign Import Transaction when cancelled"""
	fit = frappe.qb.DocType("Foreign Import Transaction")
	lcv = frappe.qb.DocType("Foreign Import LCV Details")
	trackers = (
		frappe.qb.from_(fit)
		.join(lcv)
		.on(lcv.parent == fit.name)
		.select(fit.name)
		.distinct()
		.where(lcv.landed_cost_voucher == doc.name)
		.run(as_dict=True)
	)

	for tracker in trackers:
		try:
			tracker_doc = frappe.get_doc("Foreign Import Transaction", tracker.name)

			# Remove LCV rows
			tracker_doc.landed_cost_vouchers = [
				row for row in tracker_doc.landed_cost_vouchers if row.landed_cost_voucher != doc.name
			]

			# Remove related exchange difference entries
			tracker_doc.exchange_differences = [
				row
				for row in tracker_doc.exchange_differences
				if not (row.reference_type == "Landed Cost Voucher" and row.reference_name == doc.name)
			]

			tracker_doc.save()

		except Exception as e:
			frappe.log_error(f"Error unlinking LCV {doc.name} from tracker {tracker.name}: {str(e)}")


def link_payment_to_import_tracker(doc, method):
	"""Link Payment Entry to Foreign Import Transaction"""
	if doc.payment_type != "Pay" or doc.party_type != "Supplier":
		return

	for tracker_data in get_open_trackers_for_payment(doc):
		# Check if payment currency matches tracker currency
		if doc.paid_to_account_currency == tracker_data.currency:
			try:
				tracker_doc = frappe.get_doc("Foreign Import Transaction", tracker_data.name)

				# Check if payment already added
				existing_payment = any(row.payment_entry == doc.name for row in tracker_doc.payments)
				if not existing_payment:
					payment_row = tracker_doc.add_payment_detail(doc.name)

					# Calculate and create exchange difference entry
					calculate_payment_exchange_difference(tracker_doc, doc, payment_row)

					doc.db_set("foreign_import_tracker", tracker_doc.name)

				break  # Link to first matching tracker only

			except Exception:
				# Instead of passing the full error as title:
				frappe.log_error(
					title=f"Error linking payment {doc.name} to tracker {tracker_doc.name}",  # keep short, <140 chars
					message=frappe.get_traceback(),
				)


def get_open_trackers_for_payment(payment_doc):
	"""Open trackers of the invoices the payment references, else all open trackers of the supplier."""
	filters = {"supplier": payment_doc.party, "status": ["in", ["Active", "Draft"]], "docstatus": 1}
	referenced_invoices = [
		row.reference_name
		for row in payment_doc.get("references") or []
		if row.reference_doctype == "Purchase Invoice"
	]
	if referenced_invoices:
		filters["purchase_invoice"] = ["in", referenced_invoices]
	return frappe.get_all(
		"Foreign Import Transaction",
		filters=filters,
		fields=["name", "purchase_invoice", "currency"],
		order_by="transaction_date desc",
	)


def unlink_payment_from_import_tracker(doc, method):
	"""Remove payment from Foreign Import Transaction when cancelled"""
	tracker_name = frappe.db.get_value("Payment Entry", doc.name, "foreign_import_tracker")

	if tracker_name:
		try:
			tracker_doc = frappe.get_doc("Foreign Import Transaction", tracker_name)

			# Remove payment rows
			tracker_doc.payments = [row for row in tracker_doc.payments if row.payment_entry != doc.name]

			# Remove related exchange difference entries and cancel JEs
			for diff_row in tracker_doc.exchange_differences:
				if diff_row.reference_type == "Payment Entry" and diff_row.reference_name == doc.name:
					if diff_row.journal_entry:
						try:
							je = frappe.get_doc("Journal Entry", diff_row.journal_entry)
							if je.docstatus == 1:
								je.cancel()
						except Exception:
							pass

			tracker_doc.exchange_differences = [
				row
				for row in tracker_doc.exchange_differences
				if not (row.reference_type == "Payment Entry" and row.reference_name == doc.name)
			]

			tracker_doc.save()

		except Exception as e:
			frappe.log_error(f"Error unlinking payment {doc.name} from tracker {tracker_name}: {str(e)}")


def calculate_payment_exchange_difference(tracker_doc, payment_doc, payment_row):
	"""Calculate exchange difference for payment and create Journal Entry"""
	settings = get_import_settings(tracker_doc.company)

	original_rate = flt(tracker_doc.original_exchange_rate)
	paid_amount, payment_rate = get_payment_foreign_amount_and_rate(tracker_doc, payment_doc)

	if abs(original_rate - payment_rate) < 0.000001:  # No significant difference
		return

	# Calculate exchange difference
	exchange_diff = paid_amount * (payment_rate - original_rate)

	if abs(exchange_diff) < flt(settings.exchange_difference_threshold):
		return  # Below threshold

	difference_type = "Gain" if exchange_diff > 0 else "Loss"

	# Create Journal Entry if auto-creation is enabled
	journal_entry = None
	if settings.auto_create_journal_entries:
		journal_entry = create_exchange_difference_je(
			tracker_doc,
			abs(exchange_diff),
			difference_type,
			payment_doc,
			f"Payment Exchange {difference_type}",
		)

	payment_row.exchange_difference = exchange_diff
	payment_row.journal_entry_created = 1 if journal_entry else 0

	tracker_doc.add_exchange_difference(
		"Payment Entry",
		payment_doc.name,
		difference_type,
		abs(exchange_diff),
		payment_doc.posting_date,
		f"Exchange {difference_type.lower()} on payment against PI {tracker_doc.purchase_invoice}",
		journal_entry.name if journal_entry else None,
	)


def get_payment_foreign_amount_and_rate(tracker_doc, payment_doc):
	"""Amount and exchange rate of the payment side booked in the tracker currency."""
	if payment_doc.paid_to_account_currency == tracker_doc.currency:
		return flt(payment_doc.received_amount), flt(payment_doc.target_exchange_rate)
	return flt(payment_doc.paid_amount), flt(payment_doc.source_exchange_rate)


def calculate_lcv_exchange_difference(tracker_doc, lcv_doc):
	"""Calculate exchange difference for LCV and create Journal Entry"""
	settings = get_import_settings(tracker_doc.company)

	if not settings.enable_lcv_exchange_tracking:
		return

	# For LCV, we calculate the impact on inventory valuation
	original_rate = flt(tracker_doc.original_exchange_rate)

	lcv_rate = flt(lcv_doc.get("conversion_rate")) or original_rate

	if abs(original_rate - lcv_rate) < 0.000001:
		return

	# Calculate LCV amount in foreign currency
	lcv_base_amount = flt(lcv_doc.total_taxes_and_charges)
	lcv_foreign_amount = lcv_base_amount / lcv_rate

	# Calculate what it would have been at original rate
	original_base_amount = lcv_foreign_amount * original_rate

	# Exchange difference
	exchange_diff = lcv_base_amount - original_base_amount

	if abs(exchange_diff) < flt(settings.exchange_difference_threshold):
		return

	difference_type = "Loss" if exchange_diff > 0 else "Gain"  # Reversed for LCV

	# Create Journal Entry
	journal_entry = None
	if settings.auto_create_journal_entries:
		journal_entry = create_exchange_difference_je(
			tracker_doc,
			abs(exchange_diff),
			difference_type,
			lcv_doc,
			f"LCV Exchange {difference_type}",
		)

	# Add exchange difference entry
	tracker_doc.add_exchange_difference(
		"Landed Cost Voucher",
		lcv_doc.name,
		difference_type,
		abs(exchange_diff),
		lcv_doc.posting_date,
		f"Exchange {difference_type.lower()} on importation costs - LCV {lcv_doc.name}",
		journal_entry.name if journal_entry else None,
	)


def create_exchange_difference_je(tracker_doc, amount, gain_loss_type, reference_doc, description):
	"""Create Journal Entry for exchange gain/loss"""
	settings = get_import_settings(tracker_doc.company)

	# Determine accounts
	if gain_loss_type == "Gain":
		debit_account = get_supplier_payable_account(tracker_doc.supplier, tracker_doc.company)
		credit_account = settings.default_exchange_gain_account or get_exchange_gain_loss_account(
			tracker_doc.company
		)
	else:
		debit_account = settings.default_exchange_loss_account or get_exchange_gain_loss_account(
			tracker_doc.company
		)
		credit_account = get_supplier_payable_account(tracker_doc.supplier, tracker_doc.company)

	if not debit_account or not credit_account:
		frappe.throw(_("Exchange Gain/Loss accounts not configured"))

	# Create Journal Entry
	je = frappe.new_doc("Journal Entry")
	je.company = tracker_doc.company
	je.posting_date = reference_doc.posting_date
	je.voucher_type = "Exchange Gain Or Loss"
	je.user_remark = f"{description} - {tracker_doc.purchase_invoice}"
	je.multi_currency = 1

	# Exchange Gain Or Loss vouchers must carry company currency amounts themselves
	je.append(
		"accounts",
		{
			"account": debit_account,
			"debit_in_account_currency": amount,
			"debit": amount,
			"exchange_rate": 1,
			"party_type": "Supplier" if is_payable_account(debit_account) else "",
			"party": tracker_doc.supplier if is_payable_account(debit_account) else "",
		},
	)
	je.append(
		"accounts",
		{
			"account": credit_account,
			"credit_in_account_currency": amount,
			"credit": amount,
			"exchange_rate": 1,
			"party_type": "Supplier" if is_payable_account(credit_account) else "",
			"party": tracker_doc.supplier if is_payable_account(credit_account) else "",
		},
	)

	je.insert()
	je.submit()

	return je


def get_import_settings(company):
	"""Get Foreign Import Settings for company"""
	settings = frappe.get_single("Foreign Import Settings")

	if not settings.company:
		settings.company = company
		settings.save()

	return settings


def get_supplier_payable_account(supplier, company):
	"""Party Account of the supplier for the company, else the company default."""
	payable_account = frappe.db.get_value(
		"Party Account",
		{"parenttype": "Supplier", "parent": supplier, "company": company},
		"account",
	)

	if not payable_account:
		payable_account = frappe.db.get_value("Company", company, "default_payable_account")

	return payable_account


def get_exchange_gain_loss_account(company):
	"""Get exchange gain/loss account for company"""
	return frappe.get_cached_value("Company", company, "exchange_gain_loss_account")


def is_payable_account(account):
	"""Check if account is a payable account"""
	account_type = frappe.get_cached_value("Account", account, "account_type")
	return account_type == "Payable"


def recalculate_import_differences(tracker_name):
	"""Recalculate all exchange differences for an import transaction"""
	tracker_doc = frappe.get_doc("Foreign Import Transaction", tracker_name)

	# Clear existing differences (but don't cancel JEs)
	tracker_doc.exchange_differences = []

	# Recalculate payment differences
	for payment_row in tracker_doc.payments:
		if payment_row.payment_entry:
			payment_doc = frappe.get_doc("Payment Entry", payment_row.payment_entry)
			calculate_payment_exchange_difference(tracker_doc, payment_doc, payment_row)

	# Recalculate LCV differences
	for lcv_row in tracker_doc.landed_cost_vouchers:
		if lcv_row.landed_cost_voucher:
			lcv_doc = frappe.get_doc("Landed Cost Voucher", lcv_row.landed_cost_voucher)
			calculate_lcv_exchange_difference(tracker_doc, lcv_doc)

	tracker_doc.save()
	return True


def update_pending_transactions():
	"""Scheduled task to update pending import transactions"""
	pending_trackers = frappe.db.sql(
		"""
        SELECT name FROM `tabForeign Import Transaction`
        WHERE status = 'Active' AND docstatus = 1
    """,
		as_dict=True,
	)

	for tracker in pending_trackers:
		try:
			tracker_doc = frappe.get_doc("Foreign Import Transaction", tracker.name)
			tracker_doc.calculate_totals()
			tracker_doc.set_status()
			tracker_doc.save()
		except Exception as e:
			frappe.log_error(f"Error updating tracker {tracker.name}: {str(e)}")


@frappe.whitelist()
def create_manual_exchange_entry(
	tracker_name, reference_type, reference_name, difference_type, amount, remarks
):
	"""Create manual exchange difference entry"""
	tracker_doc = frappe.get_doc("Foreign Import Transaction", tracker_name)

	if tracker_doc.docstatus != 1:
		frappe.throw("Transaction must be submitted to add manual entries")

	amount = flt(amount)
	if amount <= 0:
		frappe.throw("Amount must be greater than 0")

	settings = get_import_settings(tracker_doc.company)

	journal_entry = None
	if settings.auto_create_journal_entries:
		reference_doc = frappe.get_doc(reference_type, reference_name)
		journal_entry = create_exchange_difference_je(
			tracker_doc,
			amount,
			difference_type,
			reference_doc,
			f"Manual {difference_type} Entry",
		)

	tracker_doc.add_exchange_difference(
		reference_type,
		reference_name,
		difference_type,
		amount,
		nowdate(),
		remarks,
		journal_entry.name if journal_entry else None,
	)

	return tracker_doc.name


@frappe.whitelist()
def debug_payment_linking_issue(payment_entry_name):
	"""Debug why a payment entry is not linking to import tracker"""
	try:
		payment_doc = frappe.get_doc("Payment Entry", payment_entry_name)

		debug_info = {
			"payment_entry": payment_entry_name,
			"payment_details": {
				"payment_type": payment_doc.payment_type,
				"party_type": payment_doc.party_type,
				"party": payment_doc.party,
				"paid_to_account_currency": payment_doc.paid_to_account_currency,
				"source_exchange_rate": payment_doc.source_exchange_rate,
				"paid_amount": payment_doc.paid_amount,
				"docstatus": payment_doc.docstatus,
			},
			"issues": [],
			"potential_trackers": [],
		}

		# Check basic conditions
		if payment_doc.payment_type != "Pay":
			debug_info["issues"].append(f"Payment type is '{payment_doc.payment_type}', should be 'Pay'")

		if payment_doc.party_type != "Supplier":
			debug_info["issues"].append(f"Party type is '{payment_doc.party_type}', should be 'Supplier'")

		if payment_doc.docstatus != 1:
			debug_info["issues"].append(f"Payment Entry not submitted (docstatus = {payment_doc.docstatus})")

		# Find potential trackers for this supplier
		if payment_doc.party_type == "Supplier":
			trackers = frappe.db.sql(
				"""
                SELECT name, purchase_invoice, currency, original_exchange_rate,
                       invoice_amount_foreign, status, docstatus, supplier
                FROM `tabForeign Import Transaction`
                WHERE supplier = %s
                ORDER BY transaction_date DESC
            """,
				payment_doc.party,
				as_dict=True,
			)

			for tracker in trackers:
				tracker_info = {
					"name": tracker.name,
					"purchase_invoice": tracker.purchase_invoice,
					"currency": tracker.currency,
					"status": tracker.status,
					"docstatus": tracker.docstatus,
					"currency_match": payment_doc.paid_to_account_currency == tracker.currency,
					"status_ok": tracker.status in ("Active", "Draft") and tracker.docstatus == 1,
					"issues": [],
				}

				if not tracker_info["currency_match"]:
					tracker_info["issues"].append(
						f"Currency mismatch: Payment={payment_doc.paid_to_account_currency}, Tracker={tracker.currency}"
					)

				if not tracker_info["status_ok"]:
					tracker_info["issues"].append(
						f"Status issue: Status={tracker.status}, Docstatus={tracker.docstatus}"
					)

				# Check if already linked
				tracker_doc = frappe.get_doc("Foreign Import Transaction", tracker.name)
				already_linked = any(row.payment_entry == payment_doc.name for row in tracker_doc.payments)
				if already_linked:
					tracker_info["issues"].append("Payment already linked to this tracker")

				debug_info["potential_trackers"].append(tracker_info)

		return debug_info

	except Exception as e:
		return {"error": str(e)}


@frappe.whitelist()
def manually_link_payment_to_tracker(payment_entry_name, tracker_name=None):
	"""Manually link a payment entry to a foreign import tracker"""
	try:
		payment_doc = frappe.get_doc("Payment Entry", payment_entry_name)

		if not tracker_name:
			# Find the best matching tracker
			trackers = frappe.db.sql(
				"""
                SELECT name, currency, status, docstatus
                FROM `tabForeign Import Transaction`
                WHERE supplier = %s AND status IN ('Active', 'Draft') AND docstatus = 1
                ORDER BY transaction_date DESC
                LIMIT 1
            """,
				payment_doc.party,
				as_dict=True,
			)

			if not trackers:
				return {"error": "No active trackers found for this supplier"}

			tracker_name = trackers[0].name

		tracker_doc = frappe.get_doc("Foreign Import Transaction", tracker_name)

		# Validate
		if payment_doc.party != tracker_doc.supplier:
			return {
				"error": f"Payment party ({payment_doc.party}) doesn't match tracker supplier ({tracker_doc.supplier})"
			}

		# Check if already linked
		existing_payment = any(row.payment_entry == payment_doc.name for row in tracker_doc.payments)
		if existing_payment:
			return {"error": "Payment entry is already linked to this tracker"}

		# Add payment detail
		payment_row = tracker_doc.add_payment_detail(payment_doc.name)

		# Calculate and create exchange difference entry
		calculate_payment_exchange_difference(tracker_doc, payment_doc, payment_row)

		payment_doc.db_set("foreign_import_tracker", tracker_doc.name)

		return {"success": f"Payment {payment_doc.name} successfully linked to tracker {tracker_doc.name}"}

	except Exception as e:
		frappe.log_error(
			f"Error manually linking payment {payment_entry_name} to tracker {tracker_name}: {str(e)}"
		)
		return {"error": str(e)}
