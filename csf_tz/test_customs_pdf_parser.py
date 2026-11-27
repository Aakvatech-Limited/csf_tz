import unittest

from csf_tz.customs_pdf_parser import declared_item_count, tax_number, verify_item_numbers


class TestCustomsPDFParser(unittest.TestCase):
	def test_intervening_postal_code(self):
		words = [
			{"text": "3.No", "x0": 240, "top": 114.73},
			{"text": "Items", "x0": 259, "top": 114.73},
			{"text": "4.CL.", "x0": 280, "top": 114.73},
			{"text": "068896", "x0": 12, "top": 123.38},
			{"text": "1", "x0": 252, "top": 126.73},
			{"text": "PAD", "x0": 292, "top": 126.73},
		]
		self.assertEqual(declared_item_count(words), 1)

	def test_multiple_items(self):
		words = [
			{"text": "3.No", "x0": 240, "top": 100},
			{"text": "5", "x0": 252, "top": 112},
		]
		self.assertEqual(declared_item_count(words), 5)
		verify_item_numbers(5, [1, 2, 3, 4, 5])

	def test_mismatch(self):
		with self.assertRaises(ValueError):
			verify_item_numbers(2, [1, 1])

	def test_blank_tax(self):
		self.assertEqual(tax_number(""), 0)
		self.assertEqual(str(tax_number("0.20")), "0.20")
