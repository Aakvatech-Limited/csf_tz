import frappe
from frappe.model.workflow import get_workflow_name


def ensure_workflow_log_field_for_workflow(doc, method):
    """
    Runs when a workflow is saved, ensuring that the 'workflow_transition_logs' 
    field is added to the target Doctype.
    """
    doctype = doc.document_type
    ensure_workflow_log_field(doctype)


def ensure_workflow_log_field(doctype):
    """
    Ensures that the 'Workflow Transition Log' child table exists in the Doctype when a workflow is active.
    """
    if not isinstance(doctype, str):  
        doctype = doctype.get("document_type")  

    workflow = get_workflow_name(doctype)
    if not workflow:
        frappe.logger().info(f"No active workflow for {doctype}, skipping field creation.")
        return  

    existing_fields = frappe.get_all("Custom Field", filters={"dt": doctype, "fieldname": "workflow_transition_logs"})
    if existing_fields:
        frappe.logger().info(f"Field 'workflow_transition_logs' already exists in {doctype}")
        return  

    try:
        frappe.logger().info(f"Creating field 'workflow_transition_logs' in {doctype}")

        custom_field = frappe.get_doc({
            "doctype": "Custom Field",
            "dt": doctype,
            "fieldname": "workflow_transition_logs",
            "label": "Workflow Transition History",
            "fieldtype": "Table",
            "options": "Workflow Transition Log",
            "insert_after": "workflow_state",
            "allow_on_submit": 1,
            "read_only": 1,
            "permlevel": 0,
            "hidden": 0,
        })
        custom_field.insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.logger().info(f"Field 'workflow_transition_logs' successfully added to {doctype}")

    except Exception as e:
        frappe.log_error(f"Error creating workflow log field: {str(e)}", "Workflow Log Field Error")


def log_workflow_transition(doc, method):
    """
    Logs workflow transitions dynamically when a state change occurs.
    """
    workflow_name = get_workflow_name(doc.doctype)
    if not workflow_name:
        return  
        
    workflow_state_field = frappe.get_value("Workflow", workflow_name, "workflow_state_field")
    if not workflow_state_field:
        return
        
    current_state = doc.get(workflow_state_field)
    if not current_state:
        return  

    if not hasattr(doc, 'previous_workflow_state'):
        return
        
    previous_state = doc.previous_workflow_state
    
    if previous_state == current_state:
        return
        
    frappe.logger().info(f"Logging workflow transition: {doc.doctype} {doc.name} from {previous_state} to {current_state}")
    
    ensure_workflow_log_field(doc.doctype)
    
    if doc.docstatus == 1:
        try:
            # Create a direct log entry for this submission transition
            log_dict = {
                "name": frappe.generate_hash(length=10),
                "creation": frappe.utils.now(),
                "modified": frappe.utils.now(),
                "modified_by": frappe.session.user,
                "owner": frappe.session.user,
                "docstatus": 0,
                "parent": doc.name,
                "parentfield": "workflow_transition_logs",
                "parenttype": doc.doctype,
                "idx": 1000,  
                "user": frappe.session.user,
                "previous_state": previous_state,
                "current_state": current_state,
                "timestamp": frappe.utils.now()
            }
            
            # Insert directly into the database table for the child doctype
            frappe.db.sql("""
                INSERT INTO `tabWorkflow Transition Log` 
                ({0}) VALUES ({1})
            """.format(
                ", ".join(log_dict.keys()),
                ", ".join(["%s"] * len(log_dict))
            ), tuple(log_dict.values()))
            
            frappe.db.commit()
            frappe.logger().info(f"Successfully logged transition for submitted document {doc.name}")
        except Exception as e:
            frappe.log_error(f"Error logging workflow transition for submitted doc: {str(e)}", "Workflow Log Error")
    else:
        # For non-submitted documents, use the regular approach
        try:
            log_entry = frappe.get_doc({
                "doctype": "Workflow Transition Log",
                "user": frappe.session.user,
                "previous_state": previous_state,
                "current_state": current_state,
                "timestamp": frappe.utils.now(),
                "parent": doc.name,
                "parenttype": doc.doctype,
                "parentfield": "workflow_transition_logs"
            })
            log_entry.db_insert()
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Error logging workflow transition: {str(e)}", "Workflow Log Error")


def capture_workflow_state(doc, method):
    """
    Captures the current workflow state before it changes.
    Should be attached to before_save or before_update hook.
    Also captures state before submission.
    """
    workflow_name = get_workflow_name(doc.doctype)
    if not workflow_name:
        return
        
    workflow_state_field = frappe.get_value("Workflow", workflow_name, "workflow_state_field")
    if not workflow_state_field:
        return
        
    # Store the current state (which will be the "previous" state after save)
    if not doc.is_new():
        # Get the value directly from the database to be sure
        previous_state = frappe.db.get_value(doc.doctype, doc.name, workflow_state_field)
        doc.previous_workflow_state = previous_state
        
        # Special handling for document submission
        if doc.docstatus == 1 and frappe.db.get_value(doc.doctype, doc.name, "docstatus") == 0:
            frappe.logger().info(f"Document {doc.name} is being submitted - capturing workflow state")
            
            # Log this transition immediately since before_submit comes before the actual state change
            current_state = doc.get(workflow_state_field)
            
            # Create a direct log entry for this submission transition
            try:
                log_dict = {
                    "name": frappe.generate_hash(length=10),
                    "creation": frappe.utils.now(),
                    "modified": frappe.utils.now(),
                    "modified_by": frappe.session.user,
                    "owner": frappe.session.user,
                    "docstatus": 0,
                    "parent": doc.name,
                    "parentfield": "workflow_transition_logs",
                    "parenttype": doc.doctype,
                    "idx": 1000,
                    "user": frappe.session.user,
                    "previous_state": previous_state,
                    "current_state": current_state,
                    "timestamp": frappe.utils.now()
                }
                
                # Ensure the field exists before trying to log
                ensure_workflow_log_field(doc.doctype)
                
                # Insert directly into the database
                frappe.db.sql("""
                    INSERT INTO `tabWorkflow Transition Log` 
                    ({0}) VALUES ({1})
                """.format(
                    ", ".join(log_dict.keys()),
                    ", ".join(["%s"] * len(log_dict))
                ), tuple(log_dict.values()))
                
                frappe.db.commit()
                frappe.logger().info(f"Successfully logged transition for document being submitted {doc.name}")
            except Exception as e:
                frappe.log_error(f"Error logging workflow transition during submission: {str(e)}", "Workflow Log Error")
                

def setup_workflow_log_on_workflow_state_creation(doc, method):
    """
    This function runs whenever a Custom Field is created or updated.
    If the field is 'workflow_state', we'll add our workflow_transition_logs field.
    """
    # Only proceed if this is a workflow_state field
    if doc.fieldname != "workflow_state":
        return
        
    doctype = doc.dt
    
    frappe.logger().info(f"Workflow state field created/updated for {doctype}, checking if logs field needed")
    
    # Check if the logs field already exists
    existing_fields = frappe.get_all("Custom Field", 
                                    filters={"dt": doctype, "fieldname": "workflow_transition_logs"})
    if existing_fields:
        frappe.logger().info(f"Field 'workflow_transition_logs' already exists in {doctype}")
        return  
        
    try:
        frappe.logger().info(f"Creating workflow_transition_logs field for {doctype}")
        
        # Create the field dynamically
        custom_field = frappe.get_doc({
            "doctype": "Custom Field",
            "dt": doctype,
            "fieldname": "workflow_transition_logs",
            "label": "Workflow Transition History",
            "fieldtype": "Table",
            "options": "Workflow Transition Log",
            "insert_after": "workflow_state",  
            "allow_on_submit": 1,
            "read_only": 1,
            "permlevel": 0,
            "hidden": 0,
        })
        custom_field.insert(ignore_permissions=True)
        frappe.db.commit()
        
        frappe.logger().info(f"Field 'workflow_transition_logs' successfully added to {doctype}")
        
    except Exception as e:
        frappe.log_error(f"Error creating workflow log field: {str(e)}", "Workflow Log Field Error")        