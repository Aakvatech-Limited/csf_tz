import frappe
from frappe import _
import qrcode
import io
import base64

@frappe.whitelist()
def generate_contact_qr(employee):
    employee_doc = frappe.get_doc("Employee", employee)

    # Retrieve contact details
    phone = employee_doc.cell_number
    email = employee_doc.personal_email or employee_doc.company_email

    # Check if both phone and email are missing
    if not phone and not email:
        frappe.throw(_("Employee must have at least a phone number or an email to generate a QR Code."))

    # Create vCard format string
    vcard = f"""BEGIN:VCARD
VERSION:3.0
N:{employee_doc.last_name};{employee_doc.first_name};;;
FN:{employee_doc.employee_name}
ORG:{frappe.defaults.get_global_default('company')}
TITLE:{employee_doc.designation}
TEL;TYPE=WORK,VOICE:{phone or ''}
EMAIL;TYPE=WORK:{email or ''}
END:VCARD"""

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
        mask_pattern=7
    )
    qr.add_data(vcard)
    qr.make(fit=True)

    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64 for displaying in the frontend
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return qr_base64
