import frappe
from frappe.utils import flt

def get_vat_amount(item, vat_group, precision=0):
    vat_amount = 0

    if str(vat_group) in ["A", "1"]:
        if (
            (item.base_net_amount + item.get("distributed_discount_amount", 0)) == item.base_amount
        ):
            # both base amounts are same if the amount is exclusive of VAT
            amount = item.base_amount * 1.18
            if precision > 0:
                vat_amount = flt(amount, precision)
            else:
                vat_amount = amount
        else:
            if precision > 0:
                vat_amount = flt(item.base_amount, precision=2)
            else:
                vat_amount = item.base_amount
    else:
        if precision > 0:
            vat_amount = flt(item.base_amount, precision=2)
        else:
            vat_amount = item.base_amount
    
    return vat_amount
