# Copyright (c) 2021, Aakvatech and contributors
# For license information, please see license.txt

import json
import re
import frappe
from frappe import _
from frappe.utils import getdate
import requests
from requests.exceptions import Timeout
from frappe.model.document import Document


class ParkingBill(Document):
    pass

@frappe.whitelist()
def check_bills_all_vehicles():
    plate_list = frappe.get_all("Vehicle", fields=['name', 'number_plate', 'license_plate'])
    
    for vehicle in plate_list:
        number_plate = vehicle.get("number_plate") or vehicle.get("license_plate")
        vehicle_name = vehicle.get("name")
        
        if number_plate:
            try:
                bill = get_bills(number_plate)
                
                # If bills are found (code 6000)
                if bill and bill.code == 6000:
                    update_bill(vehicle_name, bill)
                
                # If all bills are paid or no record found (code 6004)
                elif bill and bill.code == 6004:
                    mark_all_bills_as_paid(vehicle_name)
                    frappe.log_error(f"Vehicle {vehicle_name} ({number_plate}) has no unpaid bills. Marked as paid.")
                    
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), str(e))
    
    frappe.db.commit()


def get_bills(number_plate):
    headers = {
        'x-transfer-key': 'e9f3e572-db87-4eff-9ed6-66922f1f7f24',
    }

    url = (
        "http://termis.tarura.go.tz:6003/termis-parking-service/api/v1/parkingDetails/debts/plateNumber/"
        + number_plate
    )
    try:
        response = requests.get(url=url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            return frappe._dict(json.loads(response.text))
        else:
            res = None
            try:
                res = json.loads(response.text)
            except:
                res = response.text
            frappe.log_error(res)
            return None

    except Timeout:
        frappe.log_error(_("Timeout error for plate {0}").format(number_plate))
        return None
    except Exception as e:
        frappe.log_error(e)
        return None


def update_bill(name, bills):
    if not bills.get("data"):
        return
    for row in bills.data:
        row = frappe._dict(row)
        data = frappe._dict(row.bill)

        if frappe.db.exists("Parking Bill", data.billReference):
            doc = frappe.get_doc("Parking Bill", data.billReference)
        else:
            doc = frappe.new_doc("Parking Bill")
            doc.billreference = data.billReference
        
        doc.vehicle = name
        doc.billstatus = row.billStatus
        doc.billid = data.billId
        doc.approvedby = data.approvedBy
        doc.billdescription = data.billDescription
        doc.billpayed = 1 if data.billPayed else 0
        doc.billedamount = data.billedAmount
        doc.billcontrolnumber = data.billControlNumber
        doc.billequivalentamount = data.billEquivalentAmount
        doc.expirydate = getdate(data.expiryDate)
        doc.generateddate = getdate(data.generatedDate)
        doc.miscellaneousamount = data.miscellaneousAmount
        doc.payeremail = data.payerEmail
        doc.remarks = data.remarks
        doc.payerphone = data.payerPhone
        doc.payername = data.payerName
        doc.reminderflag = data.reminderFlag
        doc.spsystemid = data.spSystemId
        doc.billpaytype = data.billPayType
        doc.receivedtime = data.receivedTime
        doc.billcurrency = data.currency
        doc.applicationid = data.applicationId
        doc.collectioncode = data.collectionCode
        doc.type = data.type
        doc.createdby = data.createdBy
        doc.itemid = data.itemId
        doc.parkingdetailsid = data.parkingDetailsId
        
        doc.bilitems = []
        for item in data.billItems:
            item = frappe._dict(item)
            bill_item = doc.append("bilitems", {})
            bill_item.billitemrefid = item.billItemRefId
            bill_item.billitemref = item.billItemRef
            bill_item.billitemamount = item.billItemAmount
            bill_item.billitemmiscamount = item.billItemMiscAmount
            bill_item.billitemeqvamount = item.billItemEqvAmount
            bill_item.billitemdescription = item.billItemDescription
            bill_item.date = item.date
            bill_item.sourcename = item.isourceName
            bill_item.gsfcode = item.gsfCode
            bill_item.parkingdetailsid = item.parkingDetailsId
        
        doc.parkingdetails = []
        for det in row.parkingDetails:
            det = frappe._dict(det)
            detail = doc.append("parkingdetails", {})
            detail.id = det.id
            detail.collectorid = det.icollectorIdd
            detail.councilcode = det.councilCode
            detail.intime = det.inTime
            detail.outtime = det.outTime
            detail.detailinsertionstatus = det.detailInsertionStatus.get("description")
            detail.coordinates = det.coordinates

        doc.save(ignore_permissions=True)


def mark_all_bills_as_paid(vehicle_name):
    """
    Marks all unpaid bills for the given vehicle as paid when the API response indicates all bills are cleared.
    """
    unpaid_bills = frappe.get_all("Parking Bill", filters={'vehicle': vehicle_name, 'billpayed': 0})
    
    for bill in unpaid_bills:
        doc = frappe.get_doc("Parking Bill", bill['name'])
        doc.billpayed = 1  # Mark the bill as paid
        doc.save(ignore_permissions=True)
