# kcb_payments_initiation.py
# This file is the controller for the KCB Payments Initiation doctype where the file is generated and signed.

import frappe
from frappe.model.document import Document
from csf_tz.kcb.utils.crypto_utils import generate_checksum, sign_checksum_with_p12
from csf_tz.kcb.api.kcb_api import submit_file_details, upload_encrypted_file
from csf_tz.kcb.pgp import encrypt_pgp


def _clean(value) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("|", " ").replace("\r", " ").replace("\n", " ")
    return " ".join(text.split())


def _purpose(value) -> str:
    return _clean(value)[:25]


def _sanitize_file_name(value) -> str:
	text = _clean(value)
	for char in '<>:"/\\|?*':
		text = text.replace(char, "")
	return text.strip()


def _delete_file_by_url(file_url):
	if not file_url:
		return
	existing = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if existing:
		frappe.delete_doc("File", existing, ignore_permissions=True, delete_permanently=True)


class KCBPaymentsInitiation(Document):

    def validate(self):
        self._validate_unique_file_reference()

    def _validate_unique_file_reference(self):
        file_reference = _clean(self.file_reference)
        if not file_reference:
            return

        duplicate = frappe.db.get_value(
            "KCB Payments Initiation",
            {
                "file_reference": file_reference,
                "docstatus": ["!=", 2],
                "name": ["!=", self.name or ""],
            },
            "name",
        )
        if duplicate:
            frappe.throw(
                'A KCB Payments Initiation named "{0}" already exists ({1}). '
                "Please use a different File Name.".format(file_reference, duplicate)
            )

    def before_save(self):
        header = "Debit Account|Beneficiary Name|Transaction Code|Amount|Currency|Beneficiary Account|Beneficiary Clearing Code|My Ref|Beneficiary Ref|CBK Code|Ordering Customer Physical Address|Payment Purpose"

        body_lines = []
        for item in self.kcb_payments_initiation_info:
            line = (
                f"{_clean(self.debit_account)}|{_clean(item.beneficiary_name)}|{_clean(item.transaction_code)}|{_clean(item.amount)}|"
                f"{_clean(item.currency)}|{_clean(item.beneficiary_account)}|{_clean(item.beneficiary_clearing_code)}|"
                f"{_clean(item.my_ref)}|{_clean(item.beneficiary_ref)}|{_clean(item.cbk_code)}|"
                f"{_clean(item.ordering_customer_physical_address)}|{_purpose(item.payment_purpose)}"
            )
            body_lines.append(line)

        body = "\n".join(body_lines)

        total_amount = sum(
            [item.amount for item in self.kcb_payments_initiation_info if item.amount]
        )
        # Total is a trailer line (not a field per record)
        file_content = f"{header}\n{body}\n{total_amount}"
        file_bytes = file_content.encode("utf-8")

        self.file_checksum = generate_checksum(file_bytes)

        self.checksum_signature = sign_checksum_with_p12(self.file_checksum)

        settings = frappe.get_single("KCB Settings")
        public_key = getattr(settings, "pgp_public_key", None)
        if not public_key:
            frappe.throw("KCB Settings PGP public key is missing.")

        encrypted_data = encrypt_pgp(file_bytes, public_key)
        if not encrypted_data:
            frappe.throw("Encryption failed: empty result")

        file_base_name = _sanitize_file_name(self.file_reference) if self.file_reference else self.name

        # Remove the previous txt/gpg pair so renaming (or re-saving) never leaves
        # stale copies behind that could later be mistaken for supporting documents.
        _delete_file_by_url(self.payment_file)
        _delete_file_by_url(self.encrypted_file)

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
