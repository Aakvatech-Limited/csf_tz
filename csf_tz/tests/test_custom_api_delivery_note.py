from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from csf_tz.custom_api import (
	auto_close_dn,
	cancle_linked_docs,
	create_delivery_note_for_all_pending_sales_invoice,
	delete_doc,
	get_linked_docs_info,
	get_list_pending_sales_invoice,
	get_pending_sales_invoice,
	make_delivery_note,
)
from csf_tz.tests.custom_api_helpers import (
	COMPANY,
	CUSTOMER,
	WAREHOUSE,
	add_stock,
	disable_db_commit,
	make_sales_invoice,
	make_test_item,
)
from csf_tz.tests.custom_api_helpers import (
	make_delivery_note as make_plain_delivery_note,
)


def draft_delivery_notes(invoice_name):
	return frappe.get_all(
		"Delivery Note", filters={"form_sales_invoice": invoice_name, "docstatus": 0}, pluck="name"
	)


class TestAutoDeliveryNote(IntegrationTestCase):
	"""Sales Invoice submit creates a draft Delivery Note and tracks delivery status."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item = make_test_item("_CSF Auto DN Item")
		cls.service = make_test_item("_CSF Auto DN Service", is_stock_item=0)
		add_stock(cls.item.name, qty=50, rate=20)

	def setUp(self):
		disable_db_commit(self)

	def test_draft_delivery_note_is_created_on_submit(self):
		invoice = make_sales_invoice(item_code=self.item.name, qty=2)
		notes = draft_delivery_notes(invoice.name)
		self.assertEqual(len(notes), 1)
		note = frappe.get_doc("Delivery Note", notes[0])
		self.assertEqual(note.items[0].si_detail, invoice.items[0].name)
		self.assertEqual(note.items[0].qty, 2)
		self.assertEqual(invoice.delivery_status, "Not Delivered")
		self.assertEqual(invoice.items[0].delivery_status, "Not Delivered")

	def test_pending_invoice_queries(self):
		invoice = make_sales_invoice(item_code=self.item.name, qty=2)
		delete_doc("Delivery Note", draft_delivery_notes(invoice.name)[0])
		pending = get_list_pending_sales_invoice(invoice.name, WAREHOUSE)
		self.assertEqual(pending[0].name, invoice.name)
		filters = {"customer": CUSTOMER, "company": COMPANY, "set_warehouse": WAREHOUSE}
		names = [row.name for row in get_pending_sales_invoice("Sales Invoice", "", "name", 0, 50, filters)]
		self.assertIn(invoice.name, names)
		date_filters = {"posting_date": ["Between", [nowdate(), nowdate()]]}
		names = [
			row.name
			for row in get_pending_sales_invoice("Sales Invoice", invoice.name, "name", 0, 50, date_filters)
		]
		self.assertEqual(names, [invoice.name])
		self.assertEqual(get_pending_sales_invoice("Sales Invoice", "NOPE", "name", 0, 50, {}), [])

	def test_submitting_delivery_note_marks_invoice_delivered(self):
		invoice = make_sales_invoice(item_code=self.item.name, qty=2)
		note = frappe.get_doc("Delivery Note", draft_delivery_notes(invoice.name)[0])
		note.submit()
		invoice.reload()
		self.assertEqual(invoice.delivery_status, "Delivered")
		self.assertEqual(invoice.items[0].delivery_status, "Delivered")
		self.assertEqual(invoice.items[0].delivered_qty, 2)
		linked = get_linked_docs_info("Sales Invoice", invoice.name)
		self.assertIn(
			("Delivery Note", note.name, 1), [(d["doctype"], d["docname"], d["docstatus"]) for d in linked]
		)
		cancle_linked_docs([{"doctype": "Delivery Note", "docname": note.name, "docstatus": 1}])
		self.assertEqual(frappe.db.get_value("Delivery Note", note.name, "docstatus"), 2)

	def test_update_stock_invoice_is_delivered_on_submit(self):
		invoice = make_sales_invoice(item_code=self.item.name, qty=2, update_stock=1)
		self.assertEqual(draft_delivery_notes(invoice.name), [])
		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice.name, "delivery_status"), "Delivered")
		row = frappe.db.get_value(
			"Sales Invoice Item", invoice.items[0].name, ["delivered_qty", "delivery_status"], as_dict=True
		)
		self.assertEqual((row.delivered_qty, row.delivery_status), (2, "Delivered"))

	def test_non_stock_item_is_part_delivered_on_submit(self):
		invoice = make_sales_invoice(item_code=self.service.name, warehouse=None)
		self.assertEqual(draft_delivery_notes(invoice.name), [])
		self.assertEqual(
			frappe.db.get_value("Sales Invoice", invoice.name, "delivery_status"), "Part Delivered"
		)

	def test_cancel_resets_delivery_status(self):
		invoice = make_sales_invoice(item_code=self.item.name, qty=2, update_stock=1)
		invoice.reload()
		invoice.cancel()
		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice.name, "delivery_status"), "Delivered")
		invoice = make_sales_invoice(item_code=self.item.name, qty=2)
		delete_doc("Delivery Note", draft_delivery_notes(invoice.name)[0])
		invoice.reload()
		invoice.cancel()
		self.assertEqual(
			frappe.db.get_value("Sales Invoice", invoice.name, "delivery_status"), "Not Delivered"
		)
		self.assertEqual(frappe.db.get_value("Sales Invoice Item", invoice.items[0].name, "delivered_qty"), 0)

	def test_make_delivery_note_whitelisted(self):
		invoice = make_sales_invoice(item_code=self.item.name, qty=2)
		delete_doc("Delivery Note", draft_delivery_notes(invoice.name)[0])
		note = make_delivery_note(invoice.name, None, WAREHOUSE)
		self.assertEqual(note.doctype, "Delivery Note")
		self.assertEqual([(row.item_code, row.qty) for row in note.items], [(self.item.name, 2)])
		note = make_delivery_note(invoice.name, None, "_Test Warehouse 1 - _TC")
		self.assertEqual(note.items, [])
		draft = make_sales_invoice(item_code=self.item.name, qty=2, do_not_submit=True)
		self.assertRaises(frappe.ValidationError, make_delivery_note, draft.name)

	def test_scheduler_creates_notes_for_pending_invoices(self):
		invoice = make_sales_invoice(item_code=self.item.name, qty=2)
		delete_doc("Delivery Note", draft_delivery_notes(invoice.name)[0])
		create_delivery_note_for_all_pending_sales_invoice()
		self.assertEqual(len(draft_delivery_notes(invoice.name)), 1)

	def test_scheduler_skips_query_when_no_company_is_enabled(self):
		with (
			patch("csf_tz.custom_api.frappe.get_all", return_value=[]),
			patch("csf_tz.custom_api.get_list_pending_sales_invoice") as pending_invoices,
			patch("csf_tz.custom_api.create_delivery_note") as create_note,
		):
			create_delivery_note_for_all_pending_sales_invoice()
		pending_invoices.assert_not_called()
		create_note.assert_not_called()


class TestAutoCloseDeliveryNote(IntegrationTestCase):
	"""Daily job closes old Delivery Notes for customers that opted in."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.service = make_test_item("_CSF Auto Close Service", is_stock_item=0)

	def setUp(self):
		disable_db_commit(self)
		frappe.db.set_value("Customer", CUSTOMER, {"csf_tz_is_auto_close_dn": 1, "csf_tz_close_dn_after": 5})

	def test_old_notes_are_closed_and_recent_ones_kept(self):
		old = make_plain_delivery_note(
			item_code=self.service.name, warehouse=None, posting_date=add_days(nowdate(), -10)
		)
		recent = make_plain_delivery_note(
			item_code=self.service.name, warehouse=None, posting_date=add_days(nowdate(), -2)
		)
		auto_close_dn()
		self.assertEqual(frappe.db.get_value("Delivery Note", old.name, "status"), "Closed")
		self.assertNotEqual(frappe.db.get_value("Delivery Note", recent.name, "status"), "Closed")

	def test_no_customer_opted_in_is_noop(self):
		frappe.db.set_value("Customer", CUSTOMER, "csf_tz_is_auto_close_dn", 0)
		old = make_plain_delivery_note(
			item_code=self.service.name, warehouse=None, posting_date=add_days(nowdate(), -10)
		)
		auto_close_dn()
		self.assertNotEqual(frappe.db.get_value("Delivery Note", old.name, "status"), "Closed")
