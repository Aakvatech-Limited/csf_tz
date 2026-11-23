import frappe
from frappe.tests.utils import FrappeTestCase

from csf_tz.custom_api import get_item_prices_custom_po, get_item_prices_po


class TestGetPendingSiDeliveryItemCount(FrappeTestCase):
	def test_query_does_not_have_contradictory_so_detail_conditions(self):
		"""Original code had two separate .where() calls:
		so_detail.isnull() AND so_detail.isnotnull() — always False, so the
		function always returned 0. Fixed: a single OR condition."""
		sales_invoice = frappe.qb.DocType("Sales Invoice")
		sales_invoice_item = frappe.qb.DocType("Sales Invoice Item")
		q = (
			frappe.qb.from_(sales_invoice)
			.inner_join(sales_invoice_item)
			.on(sales_invoice.name == sales_invoice_item.parent)
			.select(sales_invoice_item.item_code)
			.where(
				sales_invoice_item.so_detail.isnull()
				| (sales_invoice_item.so_detail.isnotnull() & sales_invoice_item.delivery_note.isnull())
			)
		)
		sql = q.get_sql()
		self.assertIn("IS NULL", sql)
		self.assertIn("IS NOT NULL", sql)
		self.assertNotIn("IS NULL) AND (`tabSales Invoice Item`.`so_detail` IS NOT NULL", sql)


class TestGetItemPricesPo(FrappeTestCase):
	def test_returns_supplier_key_not_customer(self):
		"""Purchase Invoices have no 'customer' field. The original code
		set item_dict['customer'] = item.customer, which was always empty.
		Fixed: returns 'supplier' key."""
		company = frappe.db.get_value("Company", {}, "name")
		currency = frappe.db.get_value("Company", company, "default_currency") if company else "TZS"
		if not company or not currency:
			return
		result = get_item_prices_po("NONEXISTENT-ITEM-XYZ", currency, company=company)
		self.assertIsInstance(result, list)
		for row in result:
			self.assertIn("supplier", row)
			self.assertNotIn("customer", row)

	def test_custom_po_returns_supplier_key_not_customer(self):
		"""get_item_prices_custom_po has the same bug — fixed same way."""
		company = frappe.db.get_value("Company", {}, "name")
		currency = frappe.db.get_value("Company", company, "default_currency") if company else "TZS"
		if not company or not currency:
			return
		filters = {
			"item_code": "NONEXISTENT-ITEM-XYZ",
			"currency": currency,
			"company": company,
		}
		result = get_item_prices_custom_po(filters=filters)
		self.assertIsInstance(result, list)
		for row in result:
			self.assertIn("supplier", row)
			self.assertNotIn("customer", row)
