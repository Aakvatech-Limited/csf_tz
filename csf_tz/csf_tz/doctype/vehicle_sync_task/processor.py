import requests
from datetime import datetime
from time import sleep
import frappe

# Safe import with fallback
try:
    import csf_tz.csf_tz.doctype.vehicle_sync_task.queue as queue
except (ImportError, AttributeError) as e:
    frappe.log_error("Queue Import Warning", str(e))
    queue = None

# ------------ CONFIGURATION ------------
HOST = "https://tms.tpf.go.tz/api/OffenceCheck"
TASK_DOCTYPE = "Vehicle Sync Task"

# ------------ FALLBACK QUEUE FUNCTIONS ------------
def _reset_stuck_tasks_fallback(doctype, timeout_minutes=10):
    """Fallback implementation when queue module fails"""
    try:
        timeout_time = frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-timeout_minutes)
        Task = frappe.qb.DocType(doctype)
        
        stuck = (
            frappe.qb.from_(Task)
            .select(Task.name)
            .where(
                (Task.status == "Processing") &
                (Task.claimed_at < timeout_time) &
                ((Task.is_deleted.isnull()) | (Task.is_deleted == 0))
            )
        ).run(as_dict=True)

        for row in stuck:
            frappe.db.set_value(doctype, row["name"], {
                "status": "Pending",
                "claimed_by": "",
                "claimed_at": None,
                "next_run_at": frappe.utils.now_datetime()
            })
        return len(stuck)
    except Exception as e:
        frappe.log_error("Reset Stuck Tasks Fallback Failed", str(e))
        return 0

def _claim_batch_fallback(doctype, limit=5):
    """Fallback claim batch when queue module fails"""
    try:
        now = frappe.utils.now_datetime()
        worker_id = frappe.local.site
        Task = frappe.qb.DocType(doctype)

        rows = (
            frappe.qb.from_(Task)
            .select(Task.name)
            .where(
                (Task.status == "Pending") &
                ((Task.next_run_at.isnull()) | (Task.next_run_at <= now)) &
                ((Task.is_deleted.isnull()) | (Task.is_deleted == 0))
            )
            .orderby(Task.priority, order=frappe.qb.terms.Order.desc)
            .orderby(Task.name)
            .limit(limit)
        ).run(as_dict=True)

        if not rows:
            return []

        claimed = []
        for row in rows:
            frappe.db.set_value(doctype, row["name"], {
                "status": "Processing",
                "claimed_by": worker_id,
                "claimed_at": now,
                "last_run_at": now,
            })
            data = frappe.db.get_value(doctype, row["name"], ["name", "vehicle_no"], as_dict=True)
            claimed.append(data)
        return claimed
    except Exception as e:
        frappe.log_error("Claim Batch Fallback Failed", str(e))
        return []

def _mark_done_fallback(doctype, task):
    """Fallback mark done when queue module fails"""
    try:
        frappe.db.set_value(doctype, task["name"], {
            "status": "Done",
            "last_run_at": frappe.utils.now_datetime(),
            "claimed_by": "",
            "claimed_at": None,
            "next_run_at": None,
            "last_error": ""
        })
    except Exception as e:
        frappe.log_error("Mark Done Fallback Failed", str(e))

# ------------ API INTEGRATION ------------
def _call_external_api(vehicle_no):
    if not vehicle_no or len(vehicle_no) < 7:
        raise Exception(f"Invalid vehicle license plate: {vehicle_no}")

    payload = {"vehicle": vehicle_no}
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    try:
        sleep(2)
        response = requests.post(HOST, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
    except Exception as e:
        raise Exception(f"API/Parse error for {vehicle_no}: {str(e)}")

    # Process Fine Records
    fine_records_created, fine_records_updated = _process_fine_records(vehicle_no, result)
    
    # Process Inspection Records  
    inspection_records_created, inspection_records_updated = _process_inspection_records(vehicle_no, result)

    return {
        "status": "success",
        "vehicle": vehicle_no,
        "pending_fines": len(result.get("pending_transactions", [])),
        "fine_records_created": fine_records_created,
        "fine_records_updated": fine_records_updated,
        "inspection_records_created": inspection_records_created,
        "inspection_records_updated": inspection_records_updated,
        "total_pending_amount": result.get("totalPendingAmount", "0.00"),
        "has_inspection_data": bool(result.get("inspection_data"))
    }

def _process_fine_records(vehicle_no, result):
    """Process pending transactions into Vehicle Fine Records"""
    pending_transactions = result.get("pending_transactions", [])
    fine_records_created = 0
    fine_records_updated = 0

    if pending_transactions:
        for tx in pending_transactions:
            ref = tx.get("reference", "")
            if not ref:
                continue
                
            # Check if record exists by reference (unique field)
            existing_record = frappe.db.get_value("Vehicle Fine Record", 
                                                {"reference": ref}, 
                                                ["name", "charge", "penalty", "total", "status"])
            
            if not existing_record:
                # CREATE NEW RECORD
                try:
                    rec = frappe.new_doc("Vehicle Fine Record")
                    
                    # Proper field mapping from API to DocType
                    rec.reference = ref                          # reference
                    rec.issued_date = tx.get("issued_date", "")  # issued_date
                    rec.officer = tx.get("operator", "")         # operator -> officer
                    rec.vehicle = tx.get("vehicle", vehicle_no)  # vehicle
                    rec.licence = tx.get("licence", "")          # licence
                    rec.location = tx.get("location", "")        # location
                    rec.offence = tx.get("offence", "")          # offence
                    rec.status = tx.get("status", "PENDING")     # status
                    
                    # Currency fields - convert string to float
                    charge = float(tx.get("charge", 0)) if tx.get("charge") else 0
                    penalty = float(tx.get("penalty", 0)) if tx.get("penalty") else 0
                    
                    rec.charge = charge                          # charge
                    rec.penalty = penalty                        # penalty  
                    rec.total = charge + penalty                 # total (calculated)
                    
                    # Link to Vehicle document if exists
                    vehicle_doc = frappe.db.get_value("Vehicle", 
                                                    {"license_plate": vehicle_no}, 
                                                    "name")
                    if vehicle_doc:
                        rec.vehicle_doc = vehicle_doc            # vehicle_doc
                    
                    rec.insert(ignore_permissions=True)
                    fine_records_created += 1
                    
                except Exception as e:
                    frappe.log_error(
                        title="Vehicle Fine Record Creation Failed",
                        message=f"Error creating fine record for vehicle {vehicle_no}, reference {ref}: {str(e)}"
                    )
            else:
                # UPDATE EXISTING RECORD
                try:
                    record_name = existing_record[0] if isinstance(existing_record, tuple) else existing_record
                    
                    # Get current values
                    current_charge = existing_record[1] if isinstance(existing_record, tuple) else frappe.db.get_value("Vehicle Fine Record", record_name, "charge")
                    current_penalty = existing_record[2] if isinstance(existing_record, tuple) else frappe.db.get_value("Vehicle Fine Record", record_name, "penalty")
                    current_status = existing_record[4] if isinstance(existing_record, tuple) else frappe.db.get_value("Vehicle Fine Record", record_name, "status")
                    
                    # New values from API
                    new_charge = float(tx.get("charge", 0)) if tx.get("charge") else 0
                    new_penalty = float(tx.get("penalty", 0)) if tx.get("penalty") else 0
                    new_status = tx.get("status", "PENDING")
                    new_total = new_charge + new_penalty
                    
                    # Check if any field needs update
                    update_needed = False
                    update_data = {}
                    
                    if current_charge != new_charge:
                        update_data["charge"] = new_charge
                        update_needed = True
                        
                    if current_penalty != new_penalty:
                        update_data["penalty"] = new_penalty
                        update_needed = True
                        
                    if current_status != new_status:
                        update_data["status"] = new_status
                        update_needed = True
                    
                    # Always update total if charge/penalty changed
                    if "charge" in update_data or "penalty" in update_data:
                        update_data["total"] = new_total
                        update_needed = True
                    
                    # Update other fields that might change
                    update_data["issued_date"] = tx.get("issued_date", "")
                    update_data["officer"] = tx.get("operator", "")
                    update_data["location"] = tx.get("location", "")
                    update_data["offence"] = tx.get("offence", "")
                    
                    if update_needed or any(update_data.values()):
                        # Perform bulk update
                        frappe.db.set_value("Vehicle Fine Record", record_name, update_data)
                        fine_records_updated += 1
                        
                        frappe.logger().info(f"Updated fine record {ref} - Charge: {current_charge}→{new_charge}, Penalty: {current_penalty}→{new_penalty}, Status: {current_status}→{new_status}")
                        
                except Exception as e:
                    frappe.log_error(
                        title="Vehicle Fine Record Update Failed",
                        message=f"Error updating fine record {ref} for vehicle {vehicle_no}: {str(e)}"
                    )
    else:
        # No pending transactions - mark existing unpaid records as PAID
        try:
            existing = frappe.get_all("Vehicle Fine Record",
                filters={"vehicle": vehicle_no, "status": ["!=", "PAID"]},
                pluck="name")
            for record in existing:
                frappe.db.set_value("Vehicle Fine Record", record, "status", "PAID")
                fine_records_updated += 1
        except Exception as e:
            frappe.log_error(
                title="Vehicle Fine Record Update Failed",
                message=f"Error updating fine records to PAID for vehicle {vehicle_no}: {str(e)}"
            )

    return fine_records_created, fine_records_updated

def _process_inspection_records(vehicle_no, result):
    """Process inspection data into Vehicle Inspection Records"""
    inspection_data = result.get("inspection_data", [])
    inspection_records_created = 0
    inspection_records_updated = 0

    if inspection_data:
        for inspection in inspection_data:
            vir_no = inspection.get("vir_no", "")
            if not vir_no:
                continue
                
            # Check if record exists by VIR number (unique field)
            existing_record = frappe.db.get_value("Vehicle Inspection Record", 
                                                {"vir_no": vir_no}, 
                                                ["name", "updated_at"])
            
            if not existing_record:
                # CREATE NEW INSPECTION RECORD
                try:
                    rec = frappe.new_doc("Vehicle Inspection Record")
                    
                    # Basic Information
                    rec.vir_no = vir_no                                    # VIR Number
                    rec.inspection_id = inspection.get("id")               # Inspection ID
                    rec.vid = inspection.get("vid")                        # Vehicle ID
                    rec.noplate = inspection.get("noplate", vehicle_no)    # Vehicle Plate
                    rec.licence = inspection.get("licence", "")            # License Number
                    rec.inspection_date = inspection.get("inspection_date") # Inspection Date
                    rec.valid_until = inspection.get("valid_untill")       # Valid Until (API typo)
                    rec.final_result = inspection.get("finalresult")       # Final Result
                    
                    # Inspector Information
                    rec.inspector = inspection.get("inspector", "")        # Inspector Name
                    rec.inspector_id = inspection.get("inspector_id", "")  # Inspector ID
                    rec.email = inspection.get("email", "")                # Inspector Email
                    rec.region = inspection.get("region", "")              # Region
                    rec.district = inspection.get("district", "")          # District
                    
                    # Vehicle & Driver Information
                    rec.driver_name = inspection.get("driver_name", "")               # Driver Name
                    rec.driver_address = inspection.get("driver_address", "")         # Driver Address
                    rec.vehicle_passed_for = inspection.get("vehicle_passed_for", "") # Vehicle Type
                    rec.weight = inspection.get("weight", "")                         # Weight Category
                    rec.prohibition_on_use = inspection.get("prohibition_on_use", "") # Prohibition
                    rec.originates = inspection.get("originates", "")                 # Originates
                    
                    # Test Results (Pass/Fail)
                    rec.speed_test = inspection.get("speed_test", "")              # Speed Test
                    rec.electrical_system = inspection.get("electrical_system", "") # Electrical
                    rec.fitting_equipment = inspection.get("fitting_equipment", "") # Fitting Equipment
                    rec.braking_system = inspection.get("braking_system", "")      # Braking
                    rec.wheels = inspection.get("wheels", "")                      # Wheels
                    rec.suspension = inspection.get("suspension", "")              # Suspension
                    rec.steering = inspection.get("steering", "")                  # Steering
                    rec.engine = inspection.get("engine", "")                      # Engine
                    rec.exhaust = inspection.get("exhaust", "")                    # Exhaust
                    rec.transmission = inspection.get("transimission", "")         # Transmission (API typo)
                    rec.instruments_panel = inspection.get("instruments_panel", "") # Instruments
                    rec.dimensions = inspection.get("dimensions", "")              # Dimensions
                    rec.radiation = inspection.get("radiation", "")                # Radiation
                    
                    # Additional Information
                    rec.remarks = inspection.get("remarks", "")            # Remarks
                    rec.created_at = inspection.get("created_at", "")      # Created At
                    rec.updated_at = inspection.get("updated_at", "")      # Updated At
                    
                    # Link to Vehicle document if exists
                    vehicle_doc = frappe.db.get_value("Vehicle", 
                                                    {"license_plate": vehicle_no}, 
                                                    "name")
                    if vehicle_doc:
                        rec.vehicle_doc = vehicle_doc
                    
                    rec.insert(ignore_permissions=True)
                    inspection_records_created += 1
                    
                    frappe.logger().info(f"Created inspection record {vir_no} for vehicle {vehicle_no}")
                    
                except Exception as e:
                    frappe.log_error(
                        title="Vehicle Inspection Record Creation Failed",
                        message=f"Error creating inspection record for vehicle {vehicle_no}, VIR: {vir_no}: {str(e)}"
                    )
            else:
                # UPDATE EXISTING INSPECTION RECORD
                try:
                    record_name = existing_record[0] if isinstance(existing_record, tuple) else existing_record
                    api_updated_at = inspection.get("updated_at", "")
                    current_updated_at = existing_record[1] if isinstance(existing_record, tuple) else frappe.db.get_value("Vehicle Inspection Record", record_name, "updated_at")
                    
                    # Only update if API data is newer
                    if api_updated_at and (not current_updated_at or api_updated_at > str(current_updated_at)):
                        
                        update_data = {
                            "inspection_date": inspection.get("inspection_date"),
                            "valid_until": inspection.get("valid_untill"),
                            "final_result": inspection.get("finalresult"),
                            "inspector": inspection.get("inspector", ""),
                            "inspector_id": inspection.get("inspector_id", ""),
                            "email": inspection.get("email", ""),
                            "region": inspection.get("region", ""),
                            "district": inspection.get("district", ""),
                            "driver_name": inspection.get("driver_name", ""),
                            "driver_address": inspection.get("driver_address", ""),
                            "vehicle_passed_for": inspection.get("vehicle_passed_for", ""),
                            "weight": inspection.get("weight", ""),
                            "prohibition_on_use": inspection.get("prohibition_on_use", ""),
                            "originates": inspection.get("originates", ""),
                            "speed_test": inspection.get("speed_test", ""),
                            "electrical_system": inspection.get("electrical_system", ""),
                            "fitting_equipment": inspection.get("fitting_equipment", ""),
                            "braking_system": inspection.get("braking_system", ""),
                            "wheels": inspection.get("wheels", ""),
                            "suspension": inspection.get("suspension", ""),
                            "steering": inspection.get("steering", ""),
                            "engine": inspection.get("engine", ""),
                            "exhaust": inspection.get("exhaust", ""),
                            "transmission": inspection.get("transimission", ""),  # API typo
                            "instruments_panel": inspection.get("instruments_panel", ""),
                            "dimensions": inspection.get("dimensions", ""),
                            "radiation": inspection.get("radiation", ""),
                            "remarks": inspection.get("remarks", ""),
                            "updated_at": api_updated_at
                        }
                        
                        frappe.db.set_value("Vehicle Inspection Record", record_name, update_data)
                        inspection_records_updated += 1
                        
                        frappe.logger().info(f"Updated inspection record {vir_no} for vehicle {vehicle_no}")
                        
                except Exception as e:
                    frappe.log_error(
                        title="Vehicle Inspection Record Update Failed",
                        message=f"Error updating inspection record {vir_no} for vehicle {vehicle_no}: {str(e)}"
                    )

    return inspection_records_created, inspection_records_updated

# ------------ MAIN PROCESSOR ------------
@frappe.whitelist()
def run_vehicle_batch():
    start = datetime.utcnow()
    processed, errors = 0, 0

    try:
        # Reset stuck tasks - use queue module or fallback
        if queue and hasattr(queue, 'reset_stuck_tasks'):
            queue.reset_stuck_tasks(TASK_DOCTYPE, timeout_minutes=10)
        else:
            _reset_stuck_tasks_fallback(TASK_DOCTYPE, timeout_minutes=10)
        
        # Claim batch of tasks
        if queue and hasattr(queue, 'claim_batch'):
            tasks = queue.claim_batch(TASK_DOCTYPE, limit=5)
        else:
            tasks = _claim_batch_fallback(TASK_DOCTYPE, limit=5)
            
        if not tasks:
            return {"status": "no_tasks", "message": f"No pending tasks at {start}"}

        for task in tasks:
            try:
                _call_external_api(task["vehicle_no"])
                
                # Mark task as done
                if queue and hasattr(queue, 'mark_done'):
                    queue.mark_done(TASK_DOCTYPE, task)
                else:
                    _mark_done_fallback(TASK_DOCTYPE, task)
                    
                processed += 1
            except Exception as e:
                errors += 1
                error_msg = str(e)
                frappe.log_error(
                    title="Vehicle API Processing Failed",
                    message=f"Error processing vehicle {task.get('vehicle_no')}: {error_msg}"
                )
                
                # Handle failed task - use queue or simple fallback
                if queue and hasattr(queue, 'bump_attempts'):
                    attempts, _ = queue.bump_attempts(TASK_DOCTYPE, task)
                    if attempts >= getattr(queue, 'MAX_ATTEMPTS', 8):
                        queue.mark_failed(TASK_DOCTYPE, task, error_msg)
                    else:
                        backoff_seconds = getattr(queue, 'BASE_BACKOFF', 300) * (2 ** attempts)
                        queue.schedule_next(TASK_DOCTYPE, task, backoff_seconds, error_msg)
                else:
                    # Simple fallback - mark as pending for retry
                    frappe.db.set_value(TASK_DOCTYPE, task["name"], {
                        "status": "Pending",
                        "last_error": error_msg[:500],
                        "next_run_at": frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=5)
                    })

            # Check time budget
            time_budget = getattr(queue, 'TIME_BUDGET_SEC', 50) if queue else 50
            if (datetime.utcnow() - start).total_seconds() > time_budget:
                break

        frappe.db.commit()
        total_runtime = (datetime.utcnow() - start).total_seconds()
        return {
            "status": "completed",
            "runtime_seconds": total_runtime,
            "processed": processed,
            "errors": errors,
            "total_claimed": len(tasks)
        }
    except Exception as e:
        frappe.log_error(
            title="Vehicle Batch Processing Failed",
            message=f"Critical error in run_vehicle_batch: {str(e)}"
        )
        return {"status": "error", "message": str(e)}

# ------------ 15-MINUTE CYCLE MANAGEMENT ------------
@frappe.whitelist()
def reset_cycle():
    try:
        Task = frappe.qb.DocType(TASK_DOCTYPE)

        done_tasks = (
            frappe.qb.from_(Task)
            .select(Task.name)
            .where(Task.status == "Done")
        ).run(as_dict=True)

        completed_reset = 0
        for row in done_tasks:
            try:
                frappe.db.set_value(TASK_DOCTYPE, row["name"], {
                    "status": "Pending",
                    "next_run_at": frappe.utils.now(),
                    "claimed_by": "",
                    "claimed_at": None,
                    "last_error": ""
                })
                completed_reset += 1
            except Exception as e:
                frappe.log_error(
                    title="Task Reset Failed",
                    message=f"Error resetting completed task {row['name']}: {str(e)}"
                )

        from frappe.utils import add_to_date, now_datetime
        failed_tasks = (
            frappe.qb.from_(Task)
            .select(Task.name)
            .where((Task.status == "Failed") &
                   (Task.last_run_at < add_to_date(now_datetime(), hours=-1)))
        ).run(as_dict=True)

        failed_reset = 0
        for row in failed_tasks:
            try:
                frappe.db.set_value(TASK_DOCTYPE, row["name"], {
                    "status": "Pending",
                    "next_run_at": frappe.utils.now(),
                    "attempts": 0,
                    "backoff_exp": 0,
                    "claimed_by": "",
                    "claimed_at": None,
                })
                failed_reset += 1
            except Exception as e:
                frappe.log_error(
                    title="Failed Task Reset Error",
                    message=f"Error resetting failed task {row['name']}: {str(e)}"
                )

        frappe.db.commit()
        return {
            "cycle_reset": True,
            "completed_reset": completed_reset,
            "failed_reset": failed_reset,
            "total_reset": completed_reset + failed_reset,
        }
    except Exception as e:
        frappe.log_error(
            title="Cycle Reset Failed",
            message=f"Critical error in reset_cycle: {str(e)}"
        )
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def create_sync_task(vehicle_no, priority=0, immediate=False):
    try:
        # Check for existing active tasks (not deleted)
        existing = frappe.db.get_value(
            TASK_DOCTYPE,
            {
                "vehicle_no": vehicle_no,
                "status": ["in", ["Pending", "Processing"]],
                "is_deleted": ["!=", 1]  # Only check non-deleted tasks
            },
            "name"
        )

        if existing:
            if immediate or priority > 5:
                frappe.db.set_value(TASK_DOCTYPE, existing, {
                    "priority": max(priority, 5),
                    "next_run_at": frappe.utils.now_datetime()
                })
            return existing

        # Check if deleted task exists - reactivate it instead of creating new
        deleted_task = frappe.db.get_value(
            TASK_DOCTYPE,
            {"vehicle_no": vehicle_no, "is_deleted": 1},
            "name"
        )

        if deleted_task:
            # Reactivate deleted task
            frappe.db.set_value(TASK_DOCTYPE, deleted_task, {
                "is_deleted": 0,
                "status": "Pending",
                "priority": priority,
                "attempts": 0,
                "backoff_exp": 0,
                "next_run_at": frappe.utils.now_datetime() if immediate else None,
                "claimed_by": "",
                "claimed_at": None,
                "last_error": ""
            })
            return deleted_task

        # Create new task
        task = frappe.new_doc(TASK_DOCTYPE)
        task.vehicle_no = vehicle_no
        task.status = "Pending"
        task.priority = priority
        task.attempts = 0
        task.backoff_exp = 0
        task.is_deleted = 0  # Explicitly set to 0
        task.next_run_at = frappe.utils.now_datetime() if immediate else None
        task.insert(ignore_permissions=True)
        return task.name

    except Exception as e:
        frappe.log_error(
            title="Sync Task Creation Failed",
            message=f"Error creating sync task for vehicle {vehicle_no}: {str(e)}"
        )
        return None
@frappe.whitelist()
def seed_vehicle_sync_queue():
    """
    Updated: Handles new vehicles, existing vehicles, and marks deleted ones.
    Can be used for initial seeding AND daily sync.
    """
    try:
        # Current vehicles from Vehicle doctype
        current_vehicles = frappe.get_all(
            "Vehicle",
            fields=["license_plate", "name"],
            filters={"license_plate": ["is", "set"]}
        )


        # All existing sync tasks (including deleted ones)
        all_tasks = frappe.get_all(
            TASK_DOCTYPE,
            fields=["vehicle_no", "name", "is_deleted"]
        )


        current_plates = {
            vehicle.license_plate or vehicle.name
            for vehicle in current_vehicles if (vehicle.license_plate or vehicle.name)
        }
        existing_tasks_map = {task.vehicle_no: task for task in all_tasks}
        active_plates = {task.vehicle_no for task in all_tasks if not task.is_deleted}


        created = skipped = invalid = reactivated = deleted_marked = 0


        # Process current vehicles
        for vehicle in current_vehicles:
            try:
                number_plate = vehicle.license_plate or vehicle.name
                if number_plate:
                    if number_plate not in existing_tasks_map:
                        # New vehicle - create sync task
                        create_sync_task(number_plate, priority=0)
                        created += 1
                    elif existing_tasks_map[number_plate].is_deleted:
                        # Previously deleted vehicle is back - reactivate using create_sync_task
                        create_sync_task(number_plate, priority=0)
                        reactivated += 1
                    else:
                        # Already exists and active
                        skipped += 1
                else:
                    invalid += 1
            except Exception as e:
                frappe.log_error(
                    title="Vehicle Sync Queue Seed Error",
                    message=f"Error processing vehicle {vehicle.get('license_plate') or vehicle.get('name')}: {str(e)}"
                )


        # Mark vehicles as deleted if they don't exist in current Vehicle doctype
        for plate in active_plates:
            if plate not in current_plates:
                task_name = existing_tasks_map[plate].name
                frappe.db.set_value(TASK_DOCTYPE, task_name, "is_deleted", 1)
                deleted_marked += 1


        frappe.db.commit()


        return {
            "status": "success",
            "created": created,
            "skipped": skipped,
            "invalid": invalid,
            "reactivated": reactivated,
            "deleted_marked": deleted_marked,
            "total_vehicles": len(current_vehicles),
            "total_valid_plates": len(current_plates)
        }


    except Exception as e:
        frappe.log_error(
            title="Seed Vehicle Sync Queue Failed",
            message=f"Critical error in seed_vehicle_sync_queue: {str(e)}"
        )
        return {"status": "error", "message": str(e)}
