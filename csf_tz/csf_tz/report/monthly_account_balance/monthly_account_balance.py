# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from frappe import _
from frappe.query_builder import DocType

def execute(filters=None):
    if not filters:
        filters = {}

    # Define the GL Entry doctype
    gl_entry = DocType("GL Entry")
    
    # Build basic query to fetch all required data
    query = (
        frappe.qb.from_(gl_entry)
        .select(
            gl_entry.account,
            gl_entry.account_currency,
            gl_entry.posting_date,
            gl_entry.debit_in_account_currency,
            gl_entry.credit_in_account_currency
        )
        .where(gl_entry.is_cancelled == 0)
        .orderby(gl_entry.account)
        .orderby(gl_entry.posting_date)
    )
    
    # Add account filter if provided
    if filters.get("account"):
        # Handle both string and list formats for account filter
        if isinstance(filters.get("account"), list):
            account_list = filters.get("account")
        else:
            account_list = [acc.strip() for acc in filters.get("account").split(",")]
        query = query.where(gl_entry.account.isin(account_list))
    
    # Execute the query to get raw data
    raw_data = query.run(as_dict=True)
    
    # Process data to calculate monthly aggregations
    monthly_aggregation = {}
    
    for row in raw_data:
        # Format month as YYYY-MM
        if row.get('posting_date'):
            month = row['posting_date'].strftime('%Y-%m')
        else:
            continue
            
        # Create unique key for account-currency-month combination
        account_key = f"{row['account']}_{row['account_currency']}_{month}"
        
        if account_key not in monthly_aggregation:
            monthly_aggregation[account_key] = {
                'account': row['account'],
                'account_currency': row['account_currency'],
                'month': month,
                'monthly_net': 0
            }
        
        # Calculate monthly net (debit - credit)
        debit = flt(row.get('debit_in_account_currency', 0))
        credit = flt(row.get('credit_in_account_currency', 0))
        net_amount = debit - credit
        monthly_aggregation[account_key]['monthly_net'] += net_amount
    
    # Convert to list and sort
    monthly_data = list(monthly_aggregation.values())
    monthly_data.sort(key=lambda x: (x['account'], x['account_currency'], x['month']))
    
    # Calculate running balance (closing balance)
    account_balances = {}
    final_data = []
    
    for row in monthly_data:
        account_key = f"{row['account']}_{row['account_currency']}"
        
        if account_key not in account_balances:
            account_balances[account_key] = 0
        
        account_balances[account_key] += flt(row['monthly_net'])
        
        final_row = row.copy()
        final_row['closing_balance'] = account_balances[account_key]
        final_data.append(final_row)

    columns = [
        {"label": _("Account"), "fieldname": "account", "fieldtype": "Link", "options": "Account", "width": 220},
        {"label": _("Currency"), "fieldname": "account_currency", "fieldtype": "Data", "width": 100},
        {"label": _("Month"), "fieldname": "month", "fieldtype": "Data", "width": 100},
        {"label": _("Monthly Net"), "fieldname": "monthly_net", "fieldtype": "Currency", "width": 200},
        {"label": _("Closing Balance"), "fieldname": "closing_balance", "fieldtype": "Currency", "width": 200}
    ]

    return columns, final_data