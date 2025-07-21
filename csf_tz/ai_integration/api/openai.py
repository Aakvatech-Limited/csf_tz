import os
import frappe
from openai import OpenAI


@frappe.whitelist()
def analyze_doctype_with_openai(
    doctype_name,
    prompt,
    doc_data=None,
    force_resend=False
):
    # Check for existing
    existing_log = frappe.get_all("OpenAI Query Log", filters={
        "doctype_name": doctype_name,
        "query": prompt
    }, fields=["name", "status"], limit=1)

    if existing_log and not force_resend:
        response = frappe.get_value("OpenAI Query Log", existing_log[0].name, "response")
        return response or f"<h1> Your query has already been processed with status: {existing_log[0].status}</h1>"

    # Create new log
    query_log = frappe.get_doc({
        "doctype": "OpenAI Query Log",
        "doctype_name": doctype_name,
        "query": prompt,
        "status": "Queued",
        "resend_count": (existing_log[0].resend_count + 1) if existing_log else 1
    }).insert(ignore_permissions=True)

    frappe.enqueue(
        method=process_openai_query_log,
        queue="long",
        job_name=f"Analyze {doctype_name} with OpenAI",
        log_name=query_log.name,
        doc_data=doc_data
    )

    return f"<h1> Your query has been {query_log.status}</h1>"


def process_openai_query_log(log_name, doc_data=None):
    log = frappe.get_doc("OpenAI Query Log", log_name)

    try:
        log.status = "In Progress"
        log.save(ignore_permissions=True)

        llm_settings = frappe.get_cached_doc("LLM Settings", "LLM Settings")
        api_key = llm_settings.get_password("openai_api_key")
        if not api_key:
            frappe.throw("OpenAI API key not found in LLM Settings")

        model = llm_settings.default_model or "gpt-4"
        client = OpenAI(api_key=api_key)

        messages = [{
            "role": "system",
            "content": "You are a helpful assistant for Frappe/ERPNext development."
        }]

        # Doc data or files
        if doc_data:
            messages.append({
                "role": "user",
                "content": f"Please remember and process this documentation content for DocType '{log.doctype_name}':\n\n{doc_data}"
            })
        else:
            content_blocks = get_doc_files(log.doctype_name)
            for i, content in enumerate(content_blocks, 1):
                messages.append({
                    "role": "user",
                    "content": f"Please remember and process this file content for DocType '{log.doctype_name}' (File {i} of {len(content_blocks)}):\n\n{content}"
                })

        # Prompt for analysis
        messages.append({"role": "user", "content": log.query})

        # Send to OpenAI
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        reply = response.choices[0].message.content

        if not reply.strip().startswith("#"):
            reply = f"# {log.doctype_name} Analysis\n\n{reply}"

        log.response = reply
        log.status = "Complete"
        log.save(ignore_permissions=True)

    except Exception:
        log.status = "Failed"
        log.response = frappe.get_traceback()
        log.save(ignore_permissions=True)
        frappe.log_error("OpenAI Background Job Failed", frappe.get_traceback())


def get_doc_files(doctype_name):
    try:
        module = frappe.get_meta(doctype_name).module
        module_path = frappe.get_module_path(module)
        parts = module_path.split(os.sep)
        app_name = parts[parts.index("apps") + 1] if "apps" in parts else parts[-3]
    except Exception:
        frappe.throw(f"Cannot find app for DocType {doctype_name}")

    app_path = frappe.get_app_path(app_name)
    doctype_folder = os.path.join(app_path, frappe.scrub(module), "doctype", frappe.scrub(doctype_name))

    files = {
        "Python (.py)": os.path.join(doctype_folder, f"{frappe.scrub(doctype_name)}.py"),
        "JavaScript (.js)": os.path.join(doctype_folder, f"{frappe.scrub(doctype_name)}.js"),
        "JSON (.json)": os.path.join(doctype_folder, f"{frappe.scrub(doctype_name)}.json")
    }

    content_blocks = []
    for label, path in files.items():
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content_blocks.append(f"### {label}\n```{path.split('.')[-1]}\n{f.read()}\n```")

    if not content_blocks:
        frappe.throw("No source files (.py, .js, .json) found for this DocType.")
    
    return content_blocks
