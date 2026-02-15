# kcb_api.py
# This file handles all REST API endpoints for KCB — token generation, file upload, and file status

import frappe
import requests
from frappe.utils import get_url
from frappe.utils.file_manager import get_file


@frappe.whitelist()
@frappe.whitelist()
def is_kcb_enabled():
    settings = frappe.get_single("KCB Settings")
    return settings.enabled


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
    password = config.get_password("password")
    if not config.username or not password:
        frappe.throw("KCB Settings username/password is missing.")
    auth = (config.username, password)  # Authentication credentials
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    response = requests.post(
        config.token_url, headers=headers, auth=auth, timeout=30
    )  # Request a new token

    if response.status_code == 200:
        token_data = response.json()  # Parse the response
        # Support both KCB formats: access_token/expires_in or bearer_token/expires_in_seconds
        token = token_data.get("access_token") or token_data.get("bearer_token")
        expires_in = int(
            token_data.get("expires_in")
            or token_data.get("expires_in_seconds")
            or 3600
        )  # Extract expiry time (default 1 hour)

        if not token:
            frappe.throw(f"Token generation failed: {token_data}")

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
        frappe.throw(
            f"Token generation failed ({response.status_code}) from {config.token_url}: {response.text}"
        )


def submit_file_details(doc):
    config = frappe.get_single("KCB Settings")  # Fetch KCB settings
    token = get_kcb_token()  # Get the token

    headers = {
        "Authorization": f"Bearer {token}",  # Bearer token for authorization
        "Content-Type": "application/json",
    }

    originator_id = getattr(doc, "originator_conversation_id", None)
    if not originator_id:
        originator_id = frappe.generate_hash(length=20)
        doc.db_set("originator_conversation_id", originator_id, update_modified=False)

    payload = {
        "originatorConversationID": originator_id,  # Unique ID for the conversation
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


def upload_encrypted_file(doc):
    config = frappe.get_single("KCB Settings")  # Fetch KCB settings
    token = get_kcb_token()  # Get the token

    file_doc = frappe.get_doc(
        "File", {"file_url": doc.encrypted_file}
    )  # Get the file document
    file_content = get_file(file_doc.file_url)[1]  # Retrieve the file content

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
