# kcb_payments_initiation.py
# This file is the controller for the KCB Payments Initiation doctype where the file is generated and signed.

import frappe
from frappe.model.document import Document

from csf_tz.kcb.api.kcb_api import submit_file_details, upload_encrypted_file
from csf_tz.kcb.pgp import encrypt_pgp
from csf_tz.kcb.utils.crypto_utils import generate_checksum, sign_checksum_with_p12


def _clean(value) -> str:
	if value is None:
		return ""
	text = str(value)
	text = text.replace("|", " ").replace("\r", " ").replace("\n", " ")
	return " ".join(text.split())


def _purpose(value) -> str:
	return _clean(value)[:25]


class KCBPaymentsInitiation(Document):
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

		total_amount = sum([item.amount for item in self.kcb_payments_initiation_info if item.amount])
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

		file_base_name = self.name

		txt_file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{file_base_name}.txt",
				"attached_to_doctype": "KCB Payments Initiation",
				"attached_to_name": self.name,
				"content": file_content,
				"folder": "Home",
			}
		)
		txt_file.save()

		gpg_file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{file_base_name}.txt.gpg",
				"attached_to_doctype": "KCB Payments Initiation",
				"attached_to_name": self.name,
				"content": encrypted_data,
				"folder": "Home",
			}
		)
		gpg_file.save()

		self.payment_file = txt_file.file_url
		self.encrypted_file = gpg_file.file_url

	def on_submit(self):
		submit_file_details(self)
		upload_encrypted_file(self)
