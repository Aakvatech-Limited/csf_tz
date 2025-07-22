# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.workflow import get_workflow_name

class WorkflowTransitionHistory(Document):
    def before_insert(self):
        """Validate referenced document exists before insertion"""
        if not frappe.db.exists(self.reference_doctype, self.reference_name):
            frappe.throw(f"Referenced document {self.reference_doctype} {self.reference_name} does not exist")
        
        # Set document status if available
        if frappe.get_meta(self.reference_doctype).has_field('docstatus'):
            self.docstatus = frappe.db.get_value(self.reference_doctype, self.reference_name, 'docstatus')

    def after_insert(self):
        """Add comment to referenced document"""
        comment = f"Workflow changed from {self.previous_state} to {self.current_state}"
        frappe.get_doc({
            'doctype': 'Comment',
            'comment_type': 'Workflow',
            'reference_doctype': self.reference_doctype,
            'reference_name': self.reference_name,
            'content': comment
        }).insert(ignore_permissions=True)

def capture_workflow_state(doc, method):
    """Capture current state before changes"""
    workflow_name = get_workflow_name(doc.doctype)
    if not workflow_name:
        return
        
    workflow_state_field = frappe.get_value("Workflow", workflow_name, "workflow_state_field")
    if not workflow_state_field:
        return
        
    if not doc.is_new():
        previous_state = frappe.db.get_value(doc.doctype, doc.name, workflow_state_field)
        doc.previous_workflow_state = previous_state

def log_workflow_transition(doc, method):
    """Log transition to Workflow Transition History"""
    workflow_name = get_workflow_name(doc.doctype)
    if not workflow_name:
        return
        
    workflow_state_field = frappe.get_value("Workflow", workflow_name, "workflow_state_field")
    current_state = doc.get(workflow_state_field)
    
    if not hasattr(doc, 'previous_workflow_state') or not current_state:
        return
        
    if doc.previous_workflow_state == current_state:
        return
    
    workflow_comments = getattr(doc, 'workflow_comments', None)
    
    comment_text = f"Workflow changed from {doc.previous_workflow_state} to {current_state}"
    if workflow_comments:
        comment_text += f"\n\nComments: {workflow_comments}"
        
    try:
        # Create Workflow Transition History record
        log_entry = frappe.get_doc({
            "doctype": "Workflow Transition History",
            "reference_doctype": doc.doctype,
            "reference_name": doc.name,
            "workflow": workflow_name,
            "previous_state": doc.previous_workflow_state,
            "current_state": current_state,
            "user": frappe.session.user,
            "comments": comment_text 
        })
        log_entry.insert(ignore_permissions=True)
        
        frappe.get_doc({
            'doctype': 'Comment',
            'comment_type': 'Workflow',
            'reference_doctype': doc.doctype,
            'reference_name': doc.name,
            'content': comment_text
        }).insert(ignore_permissions=True)
        
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"Workflow log error: {str(e)}")

def delete_workflow_logs_on_doc_delete(doc, method):
    """Cleanup logs when document is deleted"""
    frappe.db.delete("Workflow Transition History", {
        "reference_doctype": doc.doctype,
        "reference_name": doc.name
    })
    frappe.db.commit()