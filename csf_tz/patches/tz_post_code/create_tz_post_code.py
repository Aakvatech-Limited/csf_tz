import frappe
import os
import json
import glob


def execute():
    """
    Read JSON files from regions_json directory and create TZ location records
    in hierarchical order: Region -> District -> Ward -> Village
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    regions_json_dir = os.path.join(script_dir, "regions_json")

    # Check if regions_json directory exists
    if not os.path.exists(regions_json_dir):
        frappe.log_error(
            "regions_json directory not found", f"Directory path: {regions_json_dir}"
        )
        return

    # Get all JSON files in the regions_json directory
    json_files = glob.glob(os.path.join(regions_json_dir, "*.json"))

    if not json_files:
        frappe.log_error("No JSON files found", f"Directory: {regions_json_dir}")
        return

    # Track created records to avoid duplicates
    created_regions = set()
    created_districts = set()
    created_wards = set()

    total_processed = 0
    total_errors = 0

    for json_file in json_files:
        try:
            file_processed, file_errors = process_json_file(
                json_file, created_regions, created_districts, created_wards
            )
            total_processed += file_processed
            total_errors += file_errors

        except Exception as e:
            error_msg = f"Error processing file {json_file}: {str(e)}"
            frappe.log_error("JSON File Processing Error", error_msg)
            print(error_msg)
            total_errors += 1

    # Final commit
    frappe.db.commit()

    print(
        f"Processing completed. Total records processed: {total_processed}, Total errors: {total_errors}"
    )


def process_json_file(
    json_file_path, created_regions, created_districts, created_wards
):
    """
    Process a single JSON file and create location records
    """
    processed_count = 0
    error_count = 0

    try:
        with open(json_file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError(f"Expected list in JSON file, got {type(data)}")

        print(
            f"Processing {os.path.basename(json_file_path)} with {len(data)} records..."
        )

        for record in data:
            try:
                if not isinstance(record, dict):
                    continue

                # Extract data from JSON record
                region_name = record.get("Region", "").strip()
                district_name = record.get("District", "").strip()
                ward_name = record.get("Ward", "").strip()
                village_name = record.get(
                    "Location", ""
                ).strip()  # Location maps to Village
                postcode = record.get("Postcode", "").strip()

                # Skip if essential data is missing
                if not all([region_name, district_name, ward_name]):
                    continue

                # Create/get region
                region_doc = create_or_get_region(region_name, created_regions)
                if not region_doc:
                    error_count += 1
                    continue

                # Create/get district
                district_doc = create_or_get_district(
                    district_name, region_name, created_districts
                )
                if not district_doc:
                    error_count += 1
                    continue

                # Create/get ward (pass district document name, not district name)
                ward_doc = create_or_get_ward(
                    ward_name, district_doc.name, created_wards
                )
                if not ward_doc:
                    error_count += 1
                    continue

                # Create village (always create as villages can have same name in different wards)
                if village_name:
                    village_doc = create_village(village_name, ward_doc.name, postcode)
                    if village_doc:
                        processed_count += 1
                    else:
                        error_count += 1
                else:
                    processed_count += 1  # Count even if no village name

            except Exception as e:
                error_msg = f"Error processing record in {json_file_path}: {str(e)}"
                frappe.log_error("Record Processing Error", error_msg)
                error_count += 1

        # Commit after each file
        frappe.db.commit()

    except Exception as e:
        error_msg = f"Error reading JSON file {json_file_path}: {str(e)}"
        frappe.log_error("JSON File Read Error", error_msg)
        error_count += 1

    return processed_count, error_count


def create_or_get_region(region_name, created_regions):
    """
    Create or get TZ Region record
    """
    if not region_name or region_name in created_regions:
        return (
            frappe.get_doc("TZ Region", region_name)
            if region_name in created_regions
            else None
        )

    try:
        # Check if region already exists
        if frappe.db.exists("TZ Region", region_name):
            created_regions.add(region_name)
            return frappe.get_doc("TZ Region", region_name)

        # Create new region
        region_doc = frappe.get_doc({"doctype": "TZ Region", "region": region_name})
        region_doc.insert(ignore_permissions=True)
        created_regions.add(region_name)

        return region_doc

    except Exception as e:
        error_msg = f"Error creating region '{region_name}': {str(e)}"
        frappe.log_error("Region Creation Error", error_msg)
        return None


def create_or_get_district(district_name, region_name, created_districts):
    """
    Create or get TZ District record
    """
    district_key = f"{district_name}|{region_name}"

    if district_key in created_districts:
        # Find existing district by name and region
        existing = frappe.db.get_value(
            "TZ District", {"district": district_name, "region": region_name}, "name"
        )
        if existing:
            return frappe.get_doc("TZ District", existing)

    try:
        # Check if district with same name and region exists
        existing = frappe.db.get_value(
            "TZ District", {"district": district_name, "region": region_name}, "name"
        )

        if existing:
            created_districts.add(district_key)
            return frappe.get_doc("TZ District", existing)

        # Create new district
        district_doc = frappe.get_doc(
            {"doctype": "TZ District", "district": district_name, "region": region_name}
        )
        district_doc.insert(ignore_permissions=True)
        created_districts.add(district_key)

        return district_doc

    except Exception as e:
        error_msg = f"Error creating district '{district_name}' in region '{region_name}': {str(e)}"
        frappe.log_error("District Creation Error", error_msg)
        return None


def create_or_get_ward(ward_name, district_doc_name, created_wards):
    """
    Create or get TZ Ward record
    district_doc_name should be the document name (e.g., 'D-0000001'), not the district field value
    """
    ward_key = f"{ward_name}|{district_doc_name}"

    if ward_key in created_wards:
        # Find existing ward by name and district document name
        existing = frappe.db.get_value(
            "TZ Ward", {"ward": ward_name, "district": district_doc_name}, "name"
        )
        if existing:
            return frappe.get_doc("TZ Ward", existing)

    try:
        # Check if ward with same name and district exists
        existing = frappe.db.get_value(
            "TZ Ward", {"ward": ward_name, "district": district_doc_name}, "name"
        )

        if existing:
            created_wards.add(ward_key)
            return frappe.get_doc("TZ Ward", existing)

        # Create new ward
        ward_doc = frappe.get_doc(
            {"doctype": "TZ Ward", "ward": ward_name, "district": district_doc_name}
        )
        ward_doc.insert(ignore_permissions=True)
        created_wards.add(ward_key)

        return ward_doc

    except Exception as e:
        error_msg = f"Error creating ward '{ward_name}' in district '{district_doc_name}': {str(e)}"
        frappe.log_error("Ward Creation Error", error_msg)
        return None


def create_village(village_name, ward_name, postcode):
    """
    Create TZ Village record
    Note: Villages are not tracked for duplicates as they can have same names in different wards
    """
    try:
        # Check if village with same name and ward already exists
        existing = frappe.db.get_value(
            "TZ Village", {"village": village_name, "ward": ward_name}, "name"
        )

        if existing:
            # Update postcode if provided and different
            if postcode:
                existing_doc = frappe.get_doc("TZ Village", existing)
                if existing_doc.postcode != postcode:
                    existing_doc.postcode = postcode
                    existing_doc.save(ignore_permissions=True)
            return frappe.get_doc("TZ Village", existing)

        # Create new village
        village_doc = frappe.get_doc(
            {
                "doctype": "TZ Village",
                "village": village_name,
                "ward": ward_name,
                "postcode": postcode or "",
            }
        )
        village_doc.insert(ignore_permissions=True)

        return village_doc

    except Exception as e:
        error_msg = (
            f"Error creating village '{village_name}' in ward '{ward_name}': {str(e)}"
        )
        frappe.log_error("Village Creation Error", error_msg)
        return None
