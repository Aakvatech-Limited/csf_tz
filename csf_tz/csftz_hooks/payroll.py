import frappe
from frappe import _
import os
from frappe.utils.background_jobs import enqueue
from io import BytesIO
from PyPDF3 import PdfFileReader, PdfFileWriter
from csf_tz import console
from frappe.model.workflow import apply_workflow
from frappe.utils import cint, flt


def before_insert_payroll_entry(doc, method):
    enable_payroll_approval = frappe.db.get_single_value(
        "CSF TZ Settings", "enable_payroll_approval"
    )
    if enable_payroll_approval:
        doc.has_payroll_approval = 1


def before_insert_salary_slip(doc, method):
    enable_payroll_approval = frappe.db.get_single_value(
        "CSF TZ Settings", "enable_payroll_approval"
    )
    if enable_payroll_approval:
        doc.has_payroll_approval = 1


def before_cancel_payroll_entry(doc, method):
    if not doc.has_payroll_approval:
        return

    doc.ignore_linked_doctypes = "GL Entry"
    salary_slips = frappe.get_all(
        "Salary Slip", filters={"payroll_entry": doc.name}, pluck="name"
    )

    journal_entry = None
    if len(salary_slips) > 0:
        for slip in salary_slips:
            try:
                slip_doc = frappe.get_doc("Salary Slip", slip)
                if not journal_entry:
                    journal_entry = slip_doc.journal_entry

                if slip_doc.docstatus == 1:
                    slip_doc.cancel()
                slip_doc.delete()
            except:
                traceback = frappe.get_traceback()
                title = _(f"Error for Salary Slip: <b>{slip_doc.name}</b>")
                frappe.log_error(traceback, title)
                continue

    if journal_entry:
        try:
            jv_doc = frappe.get_doc("Journal Entry", journal_entry)
            if jv_doc.docstatus == 1:
                jv_doc.cancel()
            jv_doc.delete()
        except:
            traceback = frappe.get_traceback()
            title = _(f"Error for Journal Entry: <b>{jv_doc.name}</b>")
            frappe.log_error(traceback, title)
            return


@frappe.whitelist()
def update_slips(payroll_entry):
    salary_slips = frappe.get_all(
        "Salary Slip",
        filters={"payroll_entry": payroll_entry, "docstatus": 0},
        pluck="name",
    )
    count = len(salary_slips)

    job = enqueue(
        method=enqueue_update_slips,
        queue="short",
        timeout=4600,
        is_async=True,
        enqueue_after_commit=False,
        job_id=f"update-salary-slips::{payroll_entry}",
        deduplicate=True,
        payroll_entry=payroll_entry,
    )

    frappe.msgprint(_("{0} Salary Slips is updated".format(count)))
    return count


def enqueue_update_slips(payroll_entry):
    salary_slips = frappe.get_all(
        "Salary Slip", filters={"payroll_entry": payroll_entry}, pluck="name"
    )

    for salary_slip in salary_slips:
        try:
            _update_salary_slip(salary_slip)
        except frappe.DocumentLockedError:
            continue
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                _("Failed to update Salary Slip {0}").format(salary_slip),
            )


@frappe.whitelist()
def update_slip(salary_slip, show_message=True):
    result = _update_salary_slip(salary_slip)
    if show_message and result == "updated":
        frappe.msgprint(_("Salary Slips is updated"))
    return result


def _update_salary_slip(salary_slip):
    ss_doc = frappe.get_doc("Salary Slip", salary_slip)
    if ss_doc.docstatus != 0:
        return "skipped"
    ss_doc.earnings = []
    ss_doc.deductions = []
    ss_doc.save()
    return "updated"


@frappe.whitelist()
def print_slips(payroll_entry):
    enqueue(
        method=enqueue_print_slips,
        queue="short",
        timeout=100000,
        is_async=True,
        job_name="print_salary_slips",
        kwargs=payroll_entry,
    )


def enqueue_print_slips(kwargs):
    console("Start Printing")
    payroll_entry = kwargs
    ss_data = frappe.get_all("Salary Slip", filters={"payroll_entry": payroll_entry})
    ss_list = []
    for i in ss_data:
        ss_list.append(i.name)
    doctype = dict({"Salary Slip": ss_list})
    print_format = ""
    default_print_format = frappe.db.get_value(
        "Property Setter",
        dict(property="default_print_format", doc_type="Salary Slip"),
        "value",
    )
    if default_print_format:
        print_format = default_print_format
    else:
        print_format = "Standard"

    pdf = download_multi_pdf(
        doctype, payroll_entry, format=print_format, no_letterhead=0
    )
    if pdf:
        ret = frappe.get_doc(
            {
                "doctype": "File",
                "attached_to_doctype": "Payroll Entry",
                "attached_to_name": payroll_entry,
                "folder": "Home/Attachments",
                "file_name": payroll_entry + ".pdf",
                "file_url": "/files/" + payroll_entry + ".pdf",
                "content": pdf,
            }
        )
        ret.save(ignore_permissions=1)
        console("Printing Finished", "The PDF file is ready in attachments")
        return ret


def download_multi_pdf(doctype, name, format=None, no_letterhead=0):
    output = PdfFileWriter()
    if isinstance(doctype, dict):
        for doctype_name in doctype:
            for doc_name in doctype[doctype_name]:
                try:
                    console(doc_name)
                    pdf_data = frappe.get_print(
                        doctype_name,
                        doc_name,
                        format,
                        as_pdf=True,
                        output=None,
                        no_letterhead=no_letterhead,
                    )

                    # Convert the PDF bytes into a file-like object
                    pdf_file = BytesIO(pdf_data)

                    # Create a PdfFileReader from the byte stream (file-like object)
                    reader = PdfFileReader(pdf_file)

                    # Add each page from the reader to the writer
                    for page_num in range(reader.getNumPages()):
                        output.addPage(reader.getPage(page_num))

                except Exception:
                    frappe.log_error(
                        f"Permission Error on doc {doc_name} of doctype {doctype_name}"
                    )
        frappe.local.response.filename = f"{name}.pdf"
    return read_multi_pdf(output)


def read_multi_pdf(output):
    fname = os.path.join("/tmp", "frappe-pdf-{0}.pdf".format(frappe.generate_hash()))
    with open(fname, "wb") as f:
        output.write(f)

    with open(fname, "rb") as fileobj:
        filedata = fileobj.read()

    return filedata


@frappe.whitelist()
def create_journal_entry(payroll_entry):
    payroll_entry_doc = frappe.get_doc("Payroll Entry", payroll_entry)
    if (
        payroll_entry_doc.docstatus != 1
        or payroll_entry_doc.salary_slips_submitted == 1
    ):
        return
    draft_slips_count = frappe.db.count(
        "Salary Slip", filters={"payroll_entry": payroll_entry, "docstatus": 0}
    )

    if draft_slips_count > 0:
        frappe.throw(_("Salary Slips are not submitted"))
    else:
        submitted_ss = payroll_entry_doc.get_sal_slip_list(ss_status=1, as_dict=True)
        jv_name = payroll_entry_doc.make_accrual_jv_entry(submitted_ss)
        jv_url = frappe.utils.get_url_to_form("Journal Entry", jv_name)
        si_msgprint = _("Journal Entry Created <a href='{0}'>{1}</a>").format(
            jv_url, jv_name
        )
        frappe.msgprint(si_msgprint)
        return "True"


def before_update_after_submit(doc, method):
    if not doc.has_payroll_approval:
        return

    # submit salary slips directly if payroll entry is approved
    if "Approved" in doc.workflow_state:
        doc.submit_salary_slips()
        return

    salary_slips = frappe.get_all(
        "Salary Slip", filters={"payroll_entry": doc.name}, pluck="name"
    )
    if len(salary_slips) == 0:
        return

    params = {"salary_slips": salary_slips, "action": get_workflow_action(doc)}

    enqueue(
        method=enqueue_apply_workflow_for_salary_slips,
        queue="short",
        timeout=100000,
        is_async=True,
        job_name="apply_workflow_for_salary_slips",
        kwargs=params,
    )


def get_workflow_action(doc):
    if doc.workflow_state == "Approval Requested":
        return "Submit"
    elif doc.workflow_state == "Change Requested":
        return "Reject"
    elif "Reviewed" in doc.workflow_state:
        return "Submit"


def enqueue_apply_workflow_for_salary_slips(kwargs):
    for slip in kwargs.get("salary_slips"):
        slip_doc = frappe.get_doc("Salary Slip", slip)

        if kwargs.get("action") == "Reject" and slip_doc.workflow_state == "Open":
            continue
        elif (
            kwargs.get("action") == "Submit"
            and slip_doc.workflow_state == "Ongoing Approval"
        ):
            continue
        elif kwargs.get("action") == "Submit" and slip_doc.workflow_state == "Approved":
            continue
        elif (
            kwargs.get("action") == "Cancel" and slip_doc.workflow_state == "Cancelled"
        ):
            continue
        elif not kwargs.get("action"):
            continue

        try:
            apply_workflow(slip_doc, kwargs.get("action"))

        except:
            traceback = frappe.get_traceback()
            title = _(f"Error for Salary Slip: <b>{slip_doc.name}</b>")
            frappe.log_error(traceback, title)
            continue


@frappe.whitelist()
def get_amounts_summary(payroll_entry):
    summary = {
        "gross_pay": 0.0,
        "net_pay": 0.0,
        "components": [],
    }

    salary_slips = frappe.get_all(
        "Salary Slip",
        filters={
            "payroll_entry": payroll_entry,
            "docstatus": ["!=", 2],
        },
        fields=["name", "gross_pay", "net_pay"],
    )

    slip_names = []
    for slip in salary_slips:
        summary["gross_pay"] += flt(slip.gross_pay)
        summary["net_pay"] += flt(slip.net_pay)
        slip_names.append(slip.name)

    tracked_components = frappe.get_all(
        "Salary Component",
        filters={"include_in_payroll_summary": 1},
        fields=["name"],
        order_by="name asc",
    )

    component_names = [component.name for component in tracked_components]
    totals_map = {}

    if slip_names and component_names:
        from frappe.query_builder.functions import Sum

        SalaryDetail = frappe.qb.DocType("Salary Detail")
        component_totals = (
            frappe.qb.from_(SalaryDetail)
            .select(
                SalaryDetail.salary_component,
                Sum(SalaryDetail.amount).as_("total"),
            )
            .where(SalaryDetail.parent.isin(slip_names))
            .where(SalaryDetail.salary_component.isin(component_names))
            .groupby(SalaryDetail.salary_component)
        ).run(as_dict=True)
        totals_map = {row.salary_component: flt(row.total) for row in component_totals}

    for component in tracked_components:
        summary["components"].append(
            {
                "component": component.name,
                "label": component.name,
                "amount": totals_map.get(component.name, 0.0),
            }
        )

    return summary
