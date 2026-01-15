# crypto_utils.py
# Yeh file encryption, checksum, aur digital signature se related functions rakhta hai

import hashlib
import frappe
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from cryptography.hazmat.backends import default_backend

# ✅ Checksum generate karne ka function (SHA-256)
def generate_checksum(file_content: str) -> str:
    return hashlib.sha256(file_content.encode("utf-8")).hexdigest()

# ✅ Checksum ko sign karne ka function using .p12 certificate
def sign_checksum_with_p12(checksum: str) -> str:
    password = frappe.conf.get("kcb_private_key_password")  # site_config se password le rahe hain
    p12_path = frappe.get_site_path("private", "files", "demo.p12")  # p12 file ka path

    with open(p12_path, 'rb') as f:
        p12_data = f.read()

    private_key, certificate, _ = load_key_and_certificates(
        p12_data,
        password.encode(),
        backend=default_backend()
    )

    if not private_key:
        frappe.throw("Private key not found in P12 file.")

    # Checksum ko sign kar rahe hain SHA1withRSA algorithm se
    signature = private_key.sign(
        checksum.encode(),
        padding.PKCS1v15(),
        hashes.SHA1()
    )

    # Signature ko base64 string me convert kar rahe hain (KCB API requirement)
    return base64.b64encode(signature).decode()
