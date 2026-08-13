import frappe
from frappe.api.v1 import get_request_form_data

CHECKIN_SYNC_FIELD = "last_sync_of_checkin"

# REST document endpoints: /api/resource/<doctype>/<name>, /api/v1/resource/...
# and the v2 equivalent /api/v2/document/<doctype>/<name>
RESOURCE_PATHS = ("/api/resource/", "/api/v1/resource/", "/api/v2/document/")


def skip_version_on_checkin_sync(doc, method=None):
    """Skip version creation when a PUT only updates `last_sync_of_checkin`.

    The biometric checkin sync updates this timestamp on every run, which would
    otherwise create a Version record for each sync.
    """
    if not _is_checkin_sync_request():
        return

    doc.flags.ignore_version = True


def _is_checkin_sync_request():
    request = getattr(frappe.local, "request", None)
    if not request or request.method != "PUT":
        return False

    if not request.path.startswith(RESOURCE_PATHS):
        return False

    data = get_request_form_data()

    return isinstance(data, dict) and list(data) == [CHECKIN_SYNC_FIELD]
