# Copyright (c) 2025, Aakvatech and Contributors
# See license.txt

import frappe
import unittest

class TestTRATAXInv(unittest.TestCase):
    def test_tra_tax_inv_creation(self):
        """Test basic TRA Tax Inv creation"""
        doc = frappe.new_doc("TRA Tax Inv")
        doc.verification_code = "TEST123_123456"
        doc.type = "Sales"
        doc.verification_status = "Pending"
        
        # This should not raise an error
        doc.validate()
        
        self.assertEqual(doc.type, "Sales")
        self.assertEqual(doc.verification_status, "Pending")
        self.assertEqual(doc.verification_code, "TEST123_123456")
