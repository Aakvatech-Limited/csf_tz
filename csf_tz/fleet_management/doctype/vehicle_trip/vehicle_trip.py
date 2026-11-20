# -*- coding: utf-8 -*-
# Copyright (c) 2015, Bravo Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import datetime
import time

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class VehicleTrip(Document):
    from csf_tz.after_sales_services.doctype.reference_payment_table.reference_payment_table import (
        update_child_table,
    )

    def onload(self):
        # Load approved fuel for main trip
        if self.transporter_type not in ["Sub-Contractor", "Self Drive"] and self.get(
            "main_route"
        ):
            consumption = frappe.db.get_value(
                "Vehicle", self.get("vehicle"), "fuel_consumption"
            )
            route = frappe.db.get_value(
                "Trip Route", self.get("main_route"), "total_distance"
            )
            approved_fuel = consumption * route
            self.set("main_approved_fuel", str(approved_fuel) + " Litres")

        # Load approved fuel for return trip
        if self.transporter_type not in ["Sub-Contractor", "Self Drive"] and self.get(
            "return_route"
        ):
            consumption = frappe.db.get_value(
                "Vehicle", self.get("vehicle"), "fuel_consumption"
            )
            route = frappe.db.get_value(
                "Trip Route", self.get("return_route"), "total_distance"
            )
            approved_fuel = consumption * route
            self.set("return_approved_fuel", str(approved_fuel) + " Litres")

        self.load_customer_contacts()

        if not self.company:
            self.company = frappe.defaults.get_user_default(
                "Company"
            ) or frappe.defaults.get_global_default("company")

    def validate(self):
        self.validate_fuel_requests()

    def before_save(self):
        # validate_requested_funds(self)
        self.validate_main_route_inputs()
        self.validate_return_route_inputs()

    def validate_fuel_requests(self):
        make_request = False

        # Check main trip
        for request in self.get("main_fuel_request"):
            if request.status == "Open":
                make_request = True

        # Check return trip
        for request in self.get("return_fuel_request"):
            if request.status == "Open":
                make_request = True

        if make_request:
            existing_fuel_request = frappe.db.get_value(
                "Fuel Request",
                {"reference_doctype": "Vehicle Trip", "reference_docname": self.name},
            )

            # Timestamp
            ts = time.time()
            timestamp = datetime.datetime.fromtimestamp(ts).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            if existing_fuel_request:
                doc = frappe.get_doc("Fuel Request", existing_fuel_request)
                doc.db_set("modified", timestamp)
                if "Fully Processed" == doc.status:
                    doc.db_set("status", "Partially Processed")
            else:
                fuel_request = frappe.new_doc("Fuel Request")
                fuel_request.update(
                    {
                        "vehicle_plate_number": self.get("vehicle_plate_number"),
                        "reference_doctype": "Vehicle Trip",
                        "reference_docname": self.name,
                        "status": "Waiting Approval",
                    }
                )
                fuel_request.insert(ignore_permissions=True)

            # Mark the requests as open
            for request in self.get("main_fuel_request"):
                if request.status == "Open":
                    request.set("status", "Requested")

            for request in self.get("return_fuel_request"):
                if request.status == "Open":
                    request.set("status", "Requested")

    def validate_main_route_inputs(self):
        loading_date = None
        offloading_date = None

        steps = self.get("main_route_steps")
        for step in steps:
            if step.location_type == "Loading Point":
                loading_date = step.loading_date
            if step.location_type == "Offloading Point":
                offloading_date = step.offloading_date
        if offloading_date and not loading_date:
            frappe.throw("Loading Date must be set before Offloading Date")

    def validate_return_route_inputs(self):
        # Check return trip
        loading_date = None
        offloading_date = None

        steps = self.get("return_route_steps")
        for step in steps:
            if step.location_type == "Loading Point":
                loading_date = step.loading_date
            if step.location_type == "Offloading Point":
                offloading_date = step.offloading_date
        if offloading_date and not loading_date:
            frappe.throw("Loading Date must be set before Offloading Date")

    def load_customer_contacts(self):
        """Loads address list and contact list in `__onload`"""
        from frappe.contacts.doctype.address.address import get_address_display

        if self.main_customer:
            filters = [
                ["Dynamic Link", "link_doctype", "=", "Customer"],
                ["Dynamic Link", "link_name", "=", self.main_customer],
                ["Dynamic Link", "parenttype", "=", "Address"],
            ]
            address_list = frappe.get_all("Address", filters=filters, fields=["*"])

            address_list = [
                a.update({"display": get_address_display(a)}) for a in address_list
            ]

            address_list = sorted(
                address_list,
                lambda a, b: (int(a.is_primary_address - b.is_primary_address))
                or (1 if a.modified - b.modified else 0),
                reverse=True,
            )

            self.set_onload("main_addr_list", {"addr_list": address_list})

        if self.main_consignee:
            filters = [
                ["Dynamic Link", "link_doctype", "=", "Customer"],
                ["Dynamic Link", "link_name", "=", self.main_consignee],
                ["Dynamic Link", "parenttype", "=", "Address"],
            ]
            address_list = frappe.get_all("Address", filters=filters, fields=["*"])

            address_list = [
                a.update({"display": get_address_display(a)}) for a in address_list
            ]

            address_list = sorted(
                address_list,
                lambda a, b: (int(a.is_primary_address - b.is_primary_address))
                or (1 if a.modified - b.modified else 0),
                reverse=True,
            )

            self.set_onload("main_consignee_addr_list", {"addr_list": address_list})

        if self.main_shipper:
            filters = [
                ["Dynamic Link", "link_doctype", "=", "Customer"],
                ["Dynamic Link", "link_name", "=", self.main_shipper],
                ["Dynamic Link", "parenttype", "=", "Address"],
            ]
            address_list = frappe.get_all("Address", filters=filters, fields=["*"])

            address_list = [
                a.update({"display": get_address_display(a)}) for a in address_list
            ]

            address_list = sorted(
                address_list,
                lambda a, b: (int(a.is_primary_address - b.is_primary_address))
                or (1 if a.modified - b.modified else 0),
                reverse=True,
            )

            self.set_onload("main_shipper_addr_list", {"addr_list": address_list})

        if self.return_customer:
            filters = [
                ["Dynamic Link", "link_doctype", "=", "Customer"],
                ["Dynamic Link", "link_name", "=", self.return_customer],
                ["Dynamic Link", "parenttype", "=", "Address"],
            ]
            address_list = frappe.get_all("Address", filters=filters, fields=["*"])

            address_list = [
                a.update({"display": get_address_display(a)}) for a in address_list
            ]

            address_list = sorted(
                address_list,
                lambda a, b: (int(a.is_primary_address - b.is_primary_address))
                or (1 if a.modified - b.modified else 0),
                reverse=True,
            )

            self.set_onload("return_addr_list", {"addr_list": address_list})

        if self.return_consignee:
            filters = [
                ["Dynamic Link", "link_doctype", "=", "Customer"],
                ["Dynamic Link", "link_name", "=", self.main_consignee],
                ["Dynamic Link", "parenttype", "=", "Address"],
            ]
            address_list = frappe.get_all("Address", filters=filters, fields=["*"])

            address_list = [
                a.update({"display": get_address_display(a)}) for a in address_list
            ]

            address_list = sorted(
                address_list,
                lambda a, b: (int(a.is_primary_address - b.is_primary_address))
                or (1 if a.modified - b.modified else 0),
                reverse=True,
            )

            self.set_onload("return_consignee_addr_list", {"addr_list": address_list})

        if self.return_shipper:
            filters = [
                ["Dynamic Link", "link_doctype", "=", "Customer"],
                ["Dynamic Link", "link_name", "=", self.main_shipper],
                ["Dynamic Link", "parenttype", "=", "Address"],
            ]
            address_list = frappe.get_all("Address", filters=filters, fields=["*"])

            address_list = [
                a.update({"display": get_address_display(a)}) for a in address_list
            ]

            address_list = sorted(
                address_list,
                lambda a, b: (int(a.is_primary_address - b.is_primary_address))
                or (1 if a.modified - b.modified else 0),
                reverse=True,
            )

            self.set_onload("return_shipper_addr_list", {"addr_list": address_list})


@frappe.whitelist()
def create_vehicle_trip(**args):
    args = frappe._dict(args)

    existing_vehicle_trip = frappe.db.get_value(
        "Vehicle Trip",
        {
            "reference_doctype": args.reference_doctype,
            "reference_docname": args.reference_docname,
        },
    )

    existing_return_trip = frappe.db.get_value(
        "Vehicle Trip",
        {
            "return_reference_doctype": args.reference_doctype,
            "return_reference_docname": args.reference_docname,
        },
    )

    if existing_vehicle_trip:
        # Mark the request as open and update modified time
        trip = frappe.get_doc("Vehicle Trip", existing_vehicle_trip)
        # doc.db_set("request_status", "open")
        # doc.db_set("modified", timestamp)
        return trip
    elif existing_return_trip:
        trip = frappe.get_doc("Vehicle Trip", existing_vehicle_trip)
        return trip
    else:
        trip = frappe.new_doc("Vehicle Trip")
        trip.update(
            {
                "reference_doctype": args.reference_doctype,
                "reference_docname": args.reference_docname,
                "status": "En Route",
                "hidden_status": 2,
            }
        )
        trip.insert(ignore_permissions=True)

        # Update transport assignment
        doc = frappe.get_doc(args.reference_doctype, args.reference_docname)
        doc.created_trip = trip.name
        doc.status = "Processed"
        doc.save()

        # If company vehicle, update vehicle status
        if args.transporter == "Bravo":
            vehicle = frappe.get_doc("Vehicle", args.vehicle)
            vehicle.status = "En Route"
            vehicle.hidden_status = 2
            vehicle.current_trip = trip.name
            vehicle.save()
        return trip


@frappe.whitelist()
def create_return_trip(**args):
    args = frappe._dict(args)

    existing_vehicle_trip = frappe.db.get_value(
        "Vehicle Trip",
        {
            "reference_doctype": args.reference_doctype,
            "reference_docname": args.reference_docname,
        },
    )

    existing_return_trip = frappe.db.get_value(
        "Vehicle Trip",
        {
            "return_reference_doctype": args.reference_doctype,
            "return_reference_docname": args.reference_docname,
        },
    )

    if existing_vehicle_trip:
        # Mark the request as open and update modified time
        trip = frappe.get_doc("Vehicle Trip", existing_vehicle_trip)
        # doc.db_set("request_status", "open")
        # doc.db_set("modified", timestamp)
        return trip
    elif existing_return_trip:
        trip = frappe.get_doc("Vehicle Trip", existing_return_trip)
        return trip
    else:
        # If internal tranport
        if args.transporter == "Bravo":
            vehicle = frappe.get_doc("Vehicle", args.vehicle)
            vehicle.status = "En Route - Returning"
            vehicle.hidden_status = 4

        doc = frappe.get_doc("Vehicle Trip", args.vehicle_trip)
        doc.return_reference_doctype = args.reference_doctype
        doc.return_reference_docname = args.reference_docname
        doc.status = "En Route - Returning"
        doc.hidden_status = 4
        doc.save()
        # for vehicle
        vehicle.current_trip = doc.name
        vehicle.save()
        return doc


@frappe.whitelist()
def make_vehicle_inspection(source_name, target_doc=None, ignore_permissions=False):
    docs = get_mapped_doc(
        "Vehicle Trip",
        source_name,
        {
            "Vehicle Trip": {
                "doctype": "Vehicle Inspection",
                "field_map": {
                    "driver_name": "driver_name",
                    "vehicle_plate_number": "vehicle_plate_number",
                    "name": "trip_reference",
                },
                "validation": {
                    "docstatus": ["=", 0],
                },
            }
        },
        target_doc,
        postprocess=None,
        ignore_permissions=ignore_permissions,
    )

    return docs


@frappe.whitelist()
def check_trip_status(**args):
    args = frappe._dict(args)
    frappe.msgprint("ok")

    # get trip
    # existing_trip = frappe.db.get_value("Vehicle Trip",
    # {"main_file_number": args.file_number})
    # frappe.msgprint("got")

    # get trip
    existing_trip = frappe.db.get_value(
        "Vehicle Trip", {"main_file_number": args.file_number}
    )
    if existing_trip:
        doc = frappe.get_doc("Vehicle Trip", existing_trip)
        status = doc.status
        frappe.msgprint(status)
        if status != "Closed":
            frappe.msgprint(
                "Cannot Close the File because it's Trip is not closed,Please Create the Trip"
            )
        else:
            return status
    else:
        frappe.msgprint(
            "Cannot Close because Trip has not been created yet for the current file"
        )


"""@frappe.whitelist()
def validate_route_inputs(**args):
	args = frappe._dict(args)

	frappe.msgprint("OOOOOKKKK")

	#trip = frappe.db.get_value("Vehicle Trip", {"name": args.name})
	#docs = frappe.get_doc("Vehicle Trip", trip)
	#steps=docs.main_route_steps

	if args.offloading_date and not args.loading_date:
		frappe.msgprint("Loading Steps must be filled before offloading",raise_exeption==True)
"""
