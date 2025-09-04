# Copyright (c) 2025, Aakvatech and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry


class TestForeignImportTransaction(FrappeTestCase):
    def setUp(self):
        """Set up test data"""
        self.company = "_Test Company"
        self.supplier = "_Test Supplier USD"
        self.currency = "USD"
        self.original_rate = 2500.0  # 1 USD = 2500 TZS
        self.payment_rate = 2600.0   # 1 USD = 2600 TZS (currency strengthened)

        # Create test supplier group if not exists
        if not frappe.db.exists("Supplier Group", "_Test Supplier Group"):
            supplier_group = frappe.get_doc({
                "doctype": "Supplier Group",
                "supplier_group_name": "_Test Supplier Group"
            })
            supplier_group.insert(ignore_permissions=True)

        # Create test supplier if not exists
        if not frappe.db.exists("Supplier", self.supplier):
            supplier_doc = frappe.get_doc({
                "doctype": "Supplier",
                "supplier_name": self.supplier,
                "supplier_group": "_Test Supplier Group",
                "supplier_type": "Company"
            })
            supplier_doc.insert(ignore_permissions=True)

        # Create Foreign Import Settings if not exists
        if not frappe.db.exists("Foreign Import Settings"):
            settings = frappe.get_doc({
                "doctype": "Foreign Import Settings",
                "company": self.company,
                "exchange_difference_threshold": 0.01,
                "auto_create_journal_entries": 0,  # Disable to avoid account setup issues
                "enable_lcv_exchange_tracking": 1
            })
            settings.insert(ignore_permissions=True)

    def tearDown(self):
        """Clean up test data"""
        # Cancel and delete test documents
        frappe.db.rollback()

    def test_automatic_tracker_creation_on_foreign_pi_submit(self):
        """Test that Foreign Import Transaction is created automatically when foreign PI is submitted"""
        # Create foreign currency Purchase Invoice
        pi = make_purchase_invoice(
            supplier=self.supplier,
            currency=self.currency,
            conversion_rate=self.original_rate,
            rate=100,
            do_not_submit=True
        )

        # Check no tracker exists before submission
        tracker_before = frappe.db.exists("Foreign Import Transaction", {"purchase_invoice": pi.name})
        self.assertIsNone(tracker_before)

        # Submit the Purchase Invoice
        pi.submit()

        # Check tracker is created after submission
        tracker_name = frappe.db.get_value("Foreign Import Transaction", {"purchase_invoice": pi.name}, "name")
        self.assertIsNotNone(tracker_name)

        # Verify tracker details
        tracker = frappe.get_doc("Foreign Import Transaction", tracker_name)
        self.assertEqual(tracker.purchase_invoice, pi.name)
        self.assertEqual(tracker.supplier, pi.supplier)
        self.assertEqual(tracker.currency, pi.currency)
        self.assertEqual(tracker.original_exchange_rate, pi.conversion_rate)
        self.assertEqual(tracker.invoice_amount_foreign, pi.grand_total)
        self.assertEqual(tracker.invoice_amount_base, pi.base_grand_total)
        self.assertEqual(tracker.status, "Active")
        self.assertEqual(tracker.docstatus, 1)

    def test_no_tracker_creation_for_base_currency_pi(self):
        """Test that no tracker is created for base currency Purchase Invoice"""
        # Get company's default currency
        company_currency = frappe.get_cached_value("Company", self.company, "default_currency")

        # Create base currency Purchase Invoice
        pi = make_purchase_invoice(
            supplier="_Test Supplier",
            currency=company_currency,  # Use actual company currency
            rate=100,
            do_not_submit=True
        )

        pi.submit()

        # Check no tracker is created
        tracker_name = frappe.db.get_value("Foreign Import Transaction", {"purchase_invoice": pi.name}, "name")
        self.assertIsNone(tracker_name)

    def test_payment_entry_linking_and_exchange_calculation(self):
        """Test that Payment Entry links to tracker and calculates exchange differences"""
        # Create foreign currency Purchase Invoice
        pi = make_purchase_invoice(
            supplier=self.supplier,
            currency=self.currency,
            conversion_rate=self.original_rate,
            rate=100,
            qty=10,  # Total: 1000 USD
            do_not_submit=True
        )
        pi.submit()

        # Get the created tracker
        tracker_name = frappe.db.get_value("Foreign Import Transaction", {"purchase_invoice": pi.name}, "name")
        tracker = frappe.get_doc("Foreign Import Transaction", tracker_name)

        # Create Payment Entry with different exchange rate
        pe = get_payment_entry("Purchase Invoice", pi.name)
        pe.source_exchange_rate = self.payment_rate  # Different rate
        pe.paid_amount = 500  # Pay half the invoice
        pe.base_paid_amount = 500 * self.payment_rate
        pe.insert()
        pe.submit()

        # Reload tracker to check if payment was linked
        tracker.reload()

        # Verify payment was linked
        self.assertEqual(len(tracker.payments), 1)
        payment_row = tracker.payments[0]
        self.assertEqual(payment_row.payment_entry, pe.name)
        self.assertEqual(payment_row.payment_amount_foreign, 500)
        self.assertEqual(payment_row.payment_exchange_rate, self.payment_rate)

        # Verify exchange difference calculation
        expected_diff = 500 * (self.payment_rate - self.original_rate)  # 500 * (2600 - 2500) = 50,000
        self.assertEqual(payment_row.exchange_difference, expected_diff)

        # Verify exchange difference entry was created
        self.assertEqual(len(tracker.exchange_differences), 1)
        diff_row = tracker.exchange_differences[0]
        self.assertEqual(diff_row.reference_type, "Payment Entry")
        self.assertEqual(diff_row.reference_name, pe.name)
        self.assertEqual(diff_row.difference_type, "Gain")  # Rate increased
        self.assertEqual(diff_row.amount, expected_diff)

        # Verify status is still Active (partial payment)
        self.assertEqual(tracker.status, "Active")

    def test_status_change_to_completed_on_full_payment(self):
        """Test that status changes to Completed when full payment is made"""
        # Create foreign currency Purchase Invoice
        pi = make_purchase_invoice(
            supplier=self.supplier,
            currency=self.currency,
            conversion_rate=self.original_rate,
            rate=100,
            qty=10,  # Total: 1000 USD
            do_not_submit=True
        )
        pi.submit()

        # Get the created tracker
        tracker_name = frappe.db.get_value("Foreign Import Transaction", {"purchase_invoice": pi.name}, "name")
        tracker = frappe.get_doc("Foreign Import Transaction", tracker_name)

        # Create Payment Entry for full amount
        pe = get_payment_entry("Purchase Invoice", pi.name)
        pe.source_exchange_rate = self.payment_rate
        pe.paid_amount = 1000  # Full payment
        pe.base_paid_amount = 1000 * self.payment_rate
        pe.insert()
        pe.submit()

        # Reload tracker
        tracker.reload()

        # Verify status changed to Completed
        self.assertEqual(tracker.status, "Completed")

    def test_exchange_loss_calculation(self):
        """Test exchange loss calculation when currency weakens"""
        # Create foreign currency Purchase Invoice
        pi = make_purchase_invoice(
            supplier=self.supplier,
            currency=self.currency,
            conversion_rate=self.original_rate,
            rate=100,
            qty=10,
            do_not_submit=True
        )
        pi.submit()

        # Get the created tracker
        tracker_name = frappe.db.get_value("Foreign Import Transaction", {"purchase_invoice": pi.name}, "name")
        tracker = frappe.get_doc("Foreign Import Transaction", tracker_name)

        # Create Payment Entry with lower exchange rate (currency weakened)
        weaker_rate = 2400.0  # 1 USD = 2400 TZS (currency weakened)
        pe = get_payment_entry("Purchase Invoice", pi.name)
        pe.source_exchange_rate = weaker_rate
        pe.paid_amount = 500
        pe.base_paid_amount = 500 * weaker_rate
        pe.insert()
        pe.submit()

        # Reload tracker
        tracker.reload()

        # Verify exchange loss calculation
        expected_diff = 500 * (weaker_rate - self.original_rate)  # 500 * (2400 - 2500) = -50,000
        payment_row = tracker.payments[0]
        self.assertEqual(payment_row.exchange_difference, expected_diff)

        # Verify exchange difference entry shows Loss
        diff_row = tracker.exchange_differences[0]
        self.assertEqual(diff_row.difference_type, "Loss")
        self.assertEqual(diff_row.amount, abs(expected_diff))  # Amount is always positive

    def test_tracker_cancellation_on_pi_cancel(self):
        """Test that tracker is cancelled when Purchase Invoice is cancelled"""
        # Create and submit foreign currency Purchase Invoice
        pi = make_purchase_invoice(
            supplier=self.supplier,
            currency=self.currency,
            conversion_rate=self.original_rate,
            rate=100,
            do_not_submit=True
        )
        pi.submit()

        # Get the created tracker
        tracker_name = frappe.db.get_value("Foreign Import Transaction", {"purchase_invoice": pi.name}, "name")
        tracker = frappe.get_doc("Foreign Import Transaction", tracker_name)
        self.assertEqual(tracker.docstatus, 1)

        # Cancel the Purchase Invoice
        pi.cancel()

        # Reload tracker and verify it's cancelled
        tracker.reload()
        self.assertEqual(tracker.docstatus, 2)
        self.assertEqual(tracker.status, "Cancelled")

    def test_currency_validation(self):
        """Test that tracker validates foreign currency requirement"""
        # Get company's default currency
        company_currency = frappe.get_cached_value("Company", self.company, "default_currency")

        # Create tracker manually with same currency as company
        tracker = frappe.get_doc({
            "doctype": "Foreign Import Transaction",
            "purchase_invoice": "TEST-PI-001",
            "supplier": self.supplier,
            "currency": company_currency,  # Same as company currency
            "company": self.company
        })

        # Should throw error on validation
        with self.assertRaises(frappe.ValidationError):
            tracker.insert()

    def test_totals_calculation(self):
        """Test that totals are calculated correctly"""
        # Create foreign currency Purchase Invoice
        pi = make_purchase_invoice(
            supplier=self.supplier,
            currency=self.currency,
            conversion_rate=self.original_rate,
            rate=100,
            qty=10,
            do_not_submit=True
        )
        pi.submit()

        # Get the created tracker
        tracker_name = frappe.db.get_value("Foreign Import Transaction", {"purchase_invoice": pi.name}, "name")
        tracker = frappe.get_doc("Foreign Import Transaction", tracker_name)

        # Add manual exchange differences
        tracker.add_exchange_difference(
            "Manual Entry", "TEST-001", "Gain", 25000, nowdate(), "Test gain"
        )
        tracker.add_exchange_difference(
            "Manual Entry", "TEST-002", "Loss", 15000, nowdate(), "Test loss"
        )

        # Verify totals
        self.assertEqual(tracker.total_gain_loss, 10000)  # 25000 - 15000
        self.assertEqual(tracker.net_difference, 10000)

    def test_exchange_summary_method(self):
        """Test the get_exchange_summary method"""
        # Create foreign currency Purchase Invoice
        pi = make_purchase_invoice(
            supplier=self.supplier,
            currency=self.currency,
            conversion_rate=self.original_rate,
            rate=100,
            qty=10,
            do_not_submit=True
        )
        pi.submit()

        # Get the created tracker
        tracker_name = frappe.db.get_value("Foreign Import Transaction", {"purchase_invoice": pi.name}, "name")
        tracker = frappe.get_doc("Foreign Import Transaction", tracker_name)

        # Create Payment Entry
        pe = get_payment_entry("Purchase Invoice", pi.name)
        pe.source_exchange_rate = self.payment_rate
        pe.paid_amount = 500
        pe.base_paid_amount = 500 * self.payment_rate
        pe.insert()
        pe.submit()

        # Reload tracker
        tracker.reload()

        # Get exchange summary
        summary = tracker.get_exchange_summary()

        # Verify summary
        expected_gain = 500 * (self.payment_rate - self.original_rate)
        self.assertEqual(summary["total_gain"], expected_gain)
        self.assertEqual(summary["total_loss"], 0)
        self.assertEqual(summary["payment_differences"], expected_gain)
        self.assertEqual(summary["lcv_differences"], 0)
        self.assertEqual(summary["manual_entries"], 0)
        self.assertEqual(summary["net_difference"], expected_gain)

    def test_no_duplicate_tracker_creation(self):
        """Test that duplicate trackers are not created for same PI"""
        # Create foreign currency Purchase Invoice
        pi = make_purchase_invoice(
            supplier=self.supplier,
            currency=self.currency,
            conversion_rate=self.original_rate,
            rate=100,
            do_not_submit=True
        )
        pi.submit()

        # Get initial tracker count
        initial_count = frappe.db.count("Foreign Import Transaction", {"purchase_invoice": pi.name})
        self.assertEqual(initial_count, 1)

        # Try to trigger tracker creation again (simulate hook being called again)
        from csf_tz.csftz_hooks.exchange_calculations import create_import_tracker
        create_import_tracker(pi, "on_submit")

        # Verify no duplicate tracker was created
        final_count = frappe.db.count("Foreign Import Transaction", {"purchase_invoice": pi.name})
        self.assertEqual(final_count, 1)

    def test_payment_currency_mismatch_no_linking(self):
        """Test that payment with different currency doesn't link to tracker"""
        # Create foreign currency Purchase Invoice in USD
        pi = make_purchase_invoice(
            supplier=self.supplier,
            currency=self.currency,  # USD
            conversion_rate=self.original_rate,
            rate=100,
            do_not_submit=True
        )
        pi.submit()

        # Get the created tracker
        tracker_name = frappe.db.get_value("Foreign Import Transaction", {"purchase_invoice": pi.name}, "name")
        tracker = frappe.get_doc("Foreign Import Transaction", tracker_name)

        # Create Payment Entry in different currency (EUR)
        pe = get_payment_entry("Purchase Invoice", pi.name)
        pe.paid_to_account_currency = "EUR"  # Different currency
        pe.source_exchange_rate = 2800.0  # EUR rate
        pe.paid_amount = 500
        pe.base_paid_amount = 500 * 2800
        pe.insert()
        pe.submit()

        # Reload tracker and verify no payment was linked
        tracker.reload()
        self.assertEqual(len(tracker.payments), 0)
        self.assertEqual(len(tracker.exchange_differences), 0)

    def test_recalculate_differences_method(self):
        """Test the recalculate_differences method"""
        # Create foreign currency Purchase Invoice
        pi = make_purchase_invoice(
            supplier=self.supplier,
            currency=self.currency,
            conversion_rate=self.original_rate,
            rate=100,
            qty=10,
            do_not_submit=True
        )
        pi.submit()

        # Get the created tracker
        tracker_name = frappe.db.get_value("Foreign Import Transaction", {"purchase_invoice": pi.name}, "name")
        tracker = frappe.get_doc("Foreign Import Transaction", tracker_name)

        # Create Payment Entry
        pe = get_payment_entry("Purchase Invoice", pi.name)
        pe.source_exchange_rate = self.payment_rate
        pe.paid_amount = 500
        pe.base_paid_amount = 500 * self.payment_rate
        pe.insert()
        pe.submit()

        # Reload tracker
        tracker.reload()
        initial_differences_count = len(tracker.exchange_differences)

        # Clear exchange differences manually
        tracker.exchange_differences = []
        tracker.save()

        # Verify differences are cleared
        tracker.reload()
        self.assertEqual(len(tracker.exchange_differences), 0)

        # Recalculate differences
        result = tracker.recalculate_differences()
        self.assertTrue(result)

        # Verify differences are recalculated
        tracker.reload()
        self.assertEqual(len(tracker.exchange_differences), initial_differences_count)
