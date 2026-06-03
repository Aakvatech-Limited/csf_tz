# crypto_utils.py
# Yeh file encryption, checksum, aur digital signature se related functions rakhta hai

import base64
import hashlib

import frappe
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from frappe import _
from frappe.utils.file_manager import get_file


def generate_checksum(file_content: str | bytes) -> str:
	if isinstance(file_content, str):
		file_content = file_content.encode("utf-8")
	return hashlib.sha256(file_content).hexdigest()


def sign_checksum_with_p12(checksum: str) -> str:
	settings = frappe.get_single("KCB Settings")
	p12_file_url = getattr(settings, "p12_file", None)
	if not p12_file_url:
		frappe.throw(_("KCB Settings P12 file is missing."))

	password = settings.get_password("p12_password")
	if not password:
		frappe.throw(_("KCB Settings P12 password is missing."))

	p12_data = get_file(p12_file_url)[1]

	private_key, certificate, _additional_certs = load_key_and_certificates(
		p12_data, password.encode(), backend=default_backend()
	)

	if not private_key:
		frappe.throw(_("Private key not found in P12 file."))

	# Checksum ko sign kar rahe hain SHA256withRSA algorithm se
	signature = private_key.sign(checksum.encode(), padding.PKCS1v15(), hashes.SHA256())

	# Signature ko base64 string me convert kar rahe hain (KCB API requirement)
	return base64.b64encode(signature).decode()
