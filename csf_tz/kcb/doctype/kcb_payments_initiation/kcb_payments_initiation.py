# kcb_payments_initiation.py
# This file is the controller for the KCB Payments Initiation doctype where the file is generated and signed.

import os
import frappe
from frappe.model.document import Document
from csf_tz.kcb.utils.crypto_utils import generate_checksum, sign_checksum_with_p12
from csf_tz.kcb.api.kcb_api import submit_file_details, upload_encrypted_file
from csf_tz.kcb.pgp import encrypt_pgp

class KCBPaymentsInitiation(Document):

    def before_save(self):
        header = "Debit Account|Beneficiary Name|Transaction Code|Amount|Currency|Beneficiary Account|Beneficiary Clearing Code|My Ref|Beneficiary Ref|CBK Code|Ordering Customer Physical Address|Payment Purpose|Total"

        body_lines = []
        for item in self.kcb_payments_initiation_info:
            line = (
                f"{self.debit_account}|{item.beneficiary_name}|{item.transaction_code}|{item.amount}|"
                f"{item.currency}|{item.beneficiary_account}|{item.beneficiary_clearing_code}|"
                f"{item.my_ref}|{item.beneficiary_ref}|{item.cbk_code}|"
                f"{item.ordering_customer_physical_address}|{item.payment_purpose}"
            )
            body_lines.append(line)

        body = "\n".join(body_lines)

        total_amount = sum(
            [item.amount for item in self.kcb_payments_initiation_info if item.amount]
        )
        file_content = f"{header}\n{body}\n{total_amount}"

        self.file_checksum = generate_checksum(file_content)

        self.checksum_signature = sign_checksum_with_p12(self.file_checksum)

        settings = frappe.get_single("KCB Settings")
        public_key = getattr(settings, "pgp_public_key", None)
        if not public_key:
            public_key_path = frappe.get_site_path("private", "files", "kcb_public_key.asc")
            if not os.path.exists(public_key_path):
                frappe.throw(
                    "KCB public key not found. Add it in KCB Settings or private/files/kcb_public_key.asc"
                )
            with open(public_key_path, "r", encoding="utf-8") as key_file:
                public_key = key_file.read()

        encrypted_data = encrypt_pgp(file_content, public_key)
        if not encrypted_data:
            frappe.throw("Encryption failed: empty result")

        file_base_name = self.name

        txt_file = frappe.get_doc({
            "doctype": "File",
            "file_name": f"{file_base_name}.txt",
            "attached_to_doctype": "KCB Payments Initiation",
            "attached_to_name": self.name,
            "content": file_content,
            "folder": "Home"
        })
        txt_file.save()

        gpg_file = frappe.get_doc({
            "doctype": "File",
            "file_name": f"{file_base_name}.txt.gpg",
            "attached_to_doctype": "KCB Payments Initiation",
            "attached_to_name": self.name,
            "content": encrypted_data,
            "folder": "Home"
        })
        gpg_file.save()

        self.payment_file = txt_file.file_url
        self.encrypted_file = gpg_file.file_url

    def on_submit(self):
        submit_file_details(self)
        upload_encrypted_file(self)
