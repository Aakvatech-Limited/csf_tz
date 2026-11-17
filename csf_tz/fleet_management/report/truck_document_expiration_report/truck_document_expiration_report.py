from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Concat


def execute(filters=None):
	columns, data = [], []
	columns = [
         {
			"fieldname": "description",
			"label": _("Document"),
			"fieldtype": "Link",
			"options": "Vehicle Documents Type",
            "width":250
		},
        
        {
			"fieldname":"expiration_date",
			"label": _("Expire Date"),
			"fieldtype": "Date",
		},
        {
			"fieldname": "type",
			"label": _("Vehicle/Trailer"),
			"fieldtype": "Data",
			"width": 150
		},
     
       
        {
			"fieldname": "reference_no",
			"label": _("Reference  Number"),
			"fieldtype": "Data",
			"width": 150
		}
	]

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))
   

	vehicle_documents = frappe.qb.DocType("Vehicle Documents")
	vehicle = frappe.qb.DocType("Vehicle")
	trailer = frappe.qb.DocType("Trailer")
	document_owner_link = (
		Case()
		.when(
			vehicle_documents.parenttype == "Vehicle",
			Concat('<a href="/desk#Form/Vehicle/', vehicle.name, '">', vehicle.number_plate, "</a>"),
		)
		.when(
			vehicle_documents.parenttype == "Trailer",
			Concat('<a href="/desk#Form/Trailer/', trailer.name, '">', trailer.number_plate, "</a>"),
		)
	)

	data = (
		frappe.qb.from_(vehicle_documents)
		.left_join(vehicle)
		.on(vehicle_documents.parent == vehicle.name)
		.left_join(trailer)
		.on(vehicle_documents.parent == trailer.name)
		.select(
			vehicle_documents.description,
			vehicle_documents.expire_date.as_("expiration_date"),
			document_owner_link.as_("type"),
			vehicle_documents.reference_no,
		)
		.where(vehicle_documents.expire_date.between(filters.from_date, filters.to_date))
	).run(as_dict=True)

	return columns, data

