# kcb_payment.py
# This file is the controller for the KCB Payment doctype where the file is generated and signed.

import frappe
from frappe.model.document import Document
from csf_tz.kcb_integration.utils.crypto_utils import generate_checksum, sign_checksum_with_p12
from csf_tz.kcb_integration.api.kcb_api import submit_file_details, upload_encrypted_file
import gnupg

class KCBPayment(Document):

    def before_save(self):
        # ✅ File Header
        header = "Field Name|Debit Account|Beneficiary Name|Transaction Code|Amount|Currency|Beneficiary Account|Beneficiary Clearing Code|Payment Purpose|Ben Physical Address|Total"

        # ✅ Child table loop se body build karna
        body_lines = []
        for item in self.kcb_payment_item:
            line = f"{self.debit_account}|{item.beneficiary_name}|{item.transaction_code}|{item.amount}|{item.currency}|{item.beneficiary_account}|{item.beneficiary_clearing_code}|{item.my_ref}|{item.ordering_customer_physical_address}"
            body_lines.append(line)

        body = "\n".join(body_lines)

        # ✅ Total amount from child rows
        total_amount = sum([item.amount for item in self.kcb_payment_item if item.amount])
        file_content = f"{header}\n{body}\n{total_amount}"

        # ✅ Checksum
        self.file_checksum = generate_checksum(file_content)

        # ✅ Digital Signature
        self.checksum_signature = sign_checksum_with_p12(self.file_checksum)

        # ✅ Encrypt file with GPG
        gpg = gnupg.GPG()
        passphrase = "my-secret-pass"
        encrypted_data = gpg.encrypt(file_content, recipients=None, symmetric='AES256', passphrase=passphrase, armor=True)

        if not encrypted_data.ok:
            frappe.throw(f"Encryption failed: {encrypted_data.status}")

        # ✅ Save plaintext file
        txt_file = frappe.get_doc({
            "doctype": "File",
            "file_name": "kcb_payment_file.txt",
            "attached_to_doctype": "KCB Payment",
            "attached_to_name": self.name,
            "content": file_content,
            "folder": "Home"
        })
        txt_file.save()

        # ✅ Save encrypted file
        gpg_file = frappe.get_doc({
            "doctype": "File",
            "file_name": "kcb_payment_file.txt.gpg",
            "attached_to_doctype": "KCB Payment",
            "attached_to_name": self.name,
            "content": str(encrypted_data),
            "folder": "Home"
        })
        gpg_file.save()

        # ✅ File URL store in parent
        self.payment_file = txt_file.file_url
        self.encrypted_file = gpg_file.file_url

    def on_submit(self):
        # ✅ Submit file metadata + encrypted file
        submit_file_details(self)
        upload_encrypted_file(self)
