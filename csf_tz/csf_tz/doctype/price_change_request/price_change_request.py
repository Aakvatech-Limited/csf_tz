# Copyright (c) 2022, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from csf_tz.api.utils import msgThrow
from frappe.utils import nowdate, get_fullname, get_url_to_form, flt
from erpnext.stock.doctype.item.item import get_last_purchase_details


class PriceChangeRequest(Document):
    def before_insert(self):
        self.posting_date = nowdate()
        self.requested_by = get_fullname(frappe.session.user)

    def validate(self):
        for row in self.items:
            validate_item(row.item_code, "validate")
            validate_price_list(row.price_list, "validate")

            old_price = set_old_price(row)
            row.old_price = old_price if old_price else 0.0  
            
            frappe.db.set_value("Price Change Request Detail", row.name, "old_price", row.old_price)

            item_details = get_last_purchase_details(row.item_code)
            if item_details:
                row.cost = flt((flt(item_details.get("base_net_rate")) * 1.0) / 1.0)
            else:
                row.cost = flt(frappe.get_cached_value("Item", row.item_code, "last_purchase_rate"))

    def before_submit(self):
        for row in self.items:
            validate_item(row.item_code, "throw")
            validate_price_list(row.price_list, "throw")
            validate_zero_prices(row)

            set_new_price_item(row, nowdate())
        self.approved_by = get_fullname(frappe.session.user)


@frappe.whitelist()
def validate_item(item, method):
    disabled = frappe.get_cached_value("Item", item, "disabled")
    if disabled == 1:
        msgThrow(_("Item: {0} is disabled".format(frappe.bold(item))), method)


@frappe.whitelist()
def validate_price_list(price_list, method):
    if not frappe.get_cached_value("Price List", price_list, "enabled"):
        msgThrow(
            _("Price List: {0} is disabled".format(frappe.bold(price_list))), method
        )


def set_old_price(item):
    """Fetch the old price of an item from Item Price"""
    
    filters = {"item_code": item.item_code, "price_list": item.price_list}
    
    if item.valid_from:
        filters["valid_from"] = [">=", item.valid_from]
    else:
        filters["valid_from"] = ["<=", nowdate()]
    
    if item.valid_to:
        filters["valid_upto"] = ["<=", item.valid_to]

    items = frappe.get_all(
        "Item Price",
        filters,
        ["name", "item_code", "price_list_rate"],
        order_by="valid_from desc",
    )
    
    if len(items) > 1:
        frappe.throw(f"Multiple Item Prices found for Item: {item.item_code} in Price List: {item.price_list}. Adjust valid from/to dates.")

    elif len(items) == 1:
        return items[0].price_list_rate

    return 0.0  


def validate_zero_prices(row):
    """Check for zero price, and stopping zero price of an item before updating item price"""

    if not row.new_price:
        frappe.throw(
            "Zero price is not allowed for an item: {0}, row: #{1}".format(
                frappe.bold(row.item_code), frappe.bold(row.idx)
            )
        )


def set_new_price_item(row, date):
    """Set new price to existing item price or create new item price"""
    filters = {
        "item_code": row.item_code,
        "price_list": row.price_list,
    }
    if row.valid_from:
        filters["valid_from"] = [">=", row.valid_from]
    else:
        filters["valid_from"] = ["<=", date]

    if row.valid_to:
        filters["valid_upto"] = ["<=", row.valid_to]

    item_price = frappe.get_all("Item Price", filters=filters)

    if len(item_price) == 0:
        record = create_new_item_price(row, date)
        if record.get("name"):
            url_to_item_price = get_url_to_form(record.doctype, record.name)
            frappe.msgprint(
                "New Item Price: <a href='{0}'>{1}</a> is created".format(
                    url_to_item_price, frappe.bold(record.name)
                )
            )

        return True

    elif len(item_price) > 1:
        msg = f"""Multiple Item Prices found for Item: <b>{row.item_code}</b> Price List: <b>{row.price_list}</b>"""
        if row.valid_from:
            msg += f" Valid From: <b>{row.valid_from}</b>"
        if row.valid_to:
            msg += f" Valid To: <b>{row.valid_to}</b>"
        frappe.throw(
            f"{msg}<br> Please delete one of them or set valid from and valid to date correctly"
        )

    else:
        frappe.set_value(
            "Item Price", item_price[0].name, "price_list_rate", row.new_price
        )


def create_new_item_price(row, date):
    """Create new item price if no any item price found for item code and price list"""

    frappe.msgprint(
        f"There is no Item price for this Item: {frappe.bold(row.item_code)} and price list: {frappe.bold(row.price_list)}.<br>New Item price will be created",
        alert=True,
    )
    new_item_price = frappe.get_doc(
        {
            "doctype": "Item Price",
            "item_code": row.item_code,
            "price_list": row.price_list,
            "price_list_rate": row.new_price,
            "valid_from": row.valid_from if row.valid_from else date,
            "valid_upto": row.valid_to if row.valid_to else None,
        }
    ).insert(ignore_permissions=True)

    return new_item_price
