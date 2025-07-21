import os
import frappe
from openai import OpenAI


"""
This is an example of how to use OpenAI's API to analyze a DocType with a prompt
"""


@frappe.whitelist()
def analyze_doctype_with_openai(
    doctype_name,
    prompt,
    doc_data=None
):  
    llm_settings = frappe.get_cached_doc("LLM Settings", "LLM Settings")
    api_key = llm_settings.get_password("openai_api_key")
    
    if not api_key:
        frappe.throw("OpenAI API key not found in LLM Settings")
    
    client = OpenAI(api_key=api_key)
    model = llm_settings.default_model or "gpt-4"
    
    messages = []
    
    def send_message_to_openai(user_message, log_title, log_details=""):
        """Helper function to send message to OpenAI and handle response"""
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        
        messages.append({
            "role": "assistant",
            "content": response.choices[0].message.content
        })
        
        frappe.log_error(
            title=log_title,
            message=f"{log_details} \n <br> {response.choices[0].message.content}"
        )
        
        return response.choices[0].message.content
    
    try:
        if doc_data:
            # Use provided JSON doc_data directly
            user_message = f"Please remember and process this documentation content for DocType '{doctype_name}':\n\n{doc_data}\n\nPlease confirm you have processed and remembered this documentation."
            send_message_to_openai(
                user_message,
                "OpenAI Doc Data Sent",
                f"Successfully sent doc_data for {doctype_name}"
            )
            
        else:
            content_blocks = get_doc_files(doctype_name)
            
            for i, content_block in enumerate(content_blocks, 1):
                # Send each file separately with memory instruction
                file_message = f"Please remember and process this file content for DocType '{doctype_name}' (File {i} of {len(content_blocks)}):\n\n{content_block}\n\nPlease confirm you have processed and remembered this file content."
                send_message_to_openai(
                    file_message,
                    "OpenAI File Sent",
                    f"Successfully sent file {i} for {doctype_name}"
                )
        
        # Step 3: Send the actual analysis prompt separately with Markdown formatting request
        analysis_prompt = f"""Now, based on all the documentation and files I've shared with you for DocType '{doctype_name}', please analyze and respond to this prompt:

        {prompt}

        Please format your response as a well-structured Markdown document with:
        - Clear headings and subheadings
        - Proper code blocks with syntax highlighting
        - Bullet points or numbered lists where appropriate
        - Tables for structured data
        - Bold and italic text for emphasis
        - Clear sections and subsections
        - Professional documentation formatting

        Make it ready for use as actual technical documentation."""

        messages.append({
            "role": "user",
            "content": analysis_prompt
        })
        
        # Get the final analysis response
        final_response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        
        # Ensure the response is properly formatted as Markdown
        markdown_content = final_response.choices[0].message.content
        
        # Add document header if not present
        if not markdown_content.strip().startswith('#'):
            markdown_content = f"# {doctype_name} Analysis\n\n{markdown_content}"
        
        return markdown_content

    except Exception as e:
        frappe.log_error(
            title="OpenAI API Call Failed",
            message=frappe.get_traceback()
        )
        frappe.throw(
            title="AI Assist Error",
            msg=str(e)
        )


def get_doc_files(doctype_name):
    try:
        module = frappe.get_meta(doctype_name).module
        module_path = frappe.get_module_path(module)

        parts = module_path.split(os.sep)
        if "apps" in parts:
            app_name = parts[parts.index("apps") + 1]
        else:
            app_name = parts[-3]  # fallback for docker/dev environments
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
    for label, file_path in files.items():
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content_blocks.append(f"\n\n### {label}\n```{file_path.split('.')[-1]}\n{f.read()}\n```")

    if not content_blocks:
        frappe.throw("No source files (.py, .js, .json) found for this DocType.")
    
    return content_blocks
