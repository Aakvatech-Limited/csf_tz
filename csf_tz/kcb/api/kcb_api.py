# kcb_api.py
# This file handles all REST API endpoints for KCB — token generation, file upload, and file status

import frappe
import requests
from frappe.utils import get_url


# ✅ Function to generate a token with caching
def get_kcb_token():
    cache_key = "kcb_token"  # Cache key for the token
    expiry_key = "kcb_token_expiry"  # Cache key for the token expiry time
    token = frappe.cache().get_value(cache_key)  # Retrieve token from cache
    expiry = frappe.cache().get_value(expiry_key)  # Retrieve expiry time from cache

    if token and expiry:
        from datetime import datetime

        # Check if the token is still valid
        if datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S") > datetime.now():
            return token  # Return the valid token

    # Generate a new token if not cached or expired
    config = frappe.get_single("KCB Settings")  # Fetch KCB settings
    auth = (config.username, config.password)  # Authentication credentials
    auth_header = {
        "Authorization": f"Basic {frappe.utils.encode(auth[0] + ':' + auth[1])}",  # Basic auth header
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    response = requests.post(
        config.token_url, headers=auth_header
    )  # Request a new token

    if response.status_code == 200:
        token_data = response.json()  # Parse the response
        token = token_data.get("access_token")  # Extract the token
        expires_in = int(
            token_data.get("expires_in", 3600)
        )  # Extract expiry time (default 1 hour)

        from datetime import datetime, timedelta

        expiry_time = datetime.now() + timedelta(
            seconds=expires_in - 60
        )  # Set expiry 1 minute earlier
        frappe.cache().set_value(cache_key, token)  # Cache the token
        frappe.cache().set_value(
            expiry_key, expiry_time.strftime("%Y-%m-%d %H:%M:%S")
        )  # Cache expiry time

        return token
    else:
        frappe.throw(f"Token generation failed: {response.text}")


# ✅ Submit file details (checksum + signature) to KCB
def submit_file_details(doc):
    config = frappe.get_single("KCB Settings")  # Fetch KCB settings
    token = get_kcb_token()  # Get the token

    headers = {
        "Authorization": f"Bearer {token}",  # Bearer token for authorization
        "Content-Type": "application/json",
    }

    payload = {
        "originatorConversationID": doc.name,  # Unique ID for the conversation
        "fileName": doc.encrypted_file.split("/")[
            -1
        ],  # Extract file name from the file path
        "supportingFilesNames": "",  # Supporting files (if any)
        "partnerCode": config.partner_code,  # Partner code from settings
        "processorCode": config.processor_code,  # Processor code from settings
        "subsidiaryCode": config.subsidiary_code,  # Subsidiary code from settings
        "templateName": config.template_name,  # Template name from settings
        "checkSum": doc.file_checksum,  # File checksum
        "checkSumSignature": doc.checksum_signature,  # Checksum signature
    }

    response = requests.post(
        config.file_details_submission_url, json=payload, headers=headers
    )  # Submit file details

    if response.status_code != 200:
        frappe.throw(
            f"File details submission failed: {response.text}"
        )  # Raise error if submission fails

    return response.json()


# ✅ Upload the actual .gpg file as multipart form-data
def upload_encrypted_file(doc):
    config = frappe.get_single("KCB Settings")  # Fetch KCB settings
    token = get_kcb_token()  # Get the token

    file_doc = frappe.get_doc(
        "File", {"file_url": doc.encrypted_file}
    )  # Get the file document
    file_content = frappe.get_file(file_doc.file_url)[1]  # Retrieve the file content

    files = {
        "file": (
            file_doc.file_name,
            file_content,
            "application/octet-stream",
        ),  # File data
        "SystemCode": (None, config.processor_code),  # System code
    }

    headers = {"Authorization": f"Bearer {token}"}  # Bearer token for authorization

    response = requests.post(
        config.file_upload_url, headers=headers, files=files
    )  # Upload the file

    if response.status_code != 200:
        frappe.throw(
            f"File upload failed: {response.text}"
        )  # Raise error if upload fails

    return response.json()
