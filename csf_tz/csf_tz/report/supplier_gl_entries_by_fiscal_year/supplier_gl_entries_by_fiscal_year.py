# Copyright (c) 2024, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Sum


def execute(filters=None):
	raw_data = get_data(filters)
	fiscal_years = get_unique_fiscal_years(raw_data)
	columns = get_columns(fiscal_years)
	result_data = build_data(raw_data, fiscal_years)
	return columns, result_data

def get_unique_fiscal_years(raw_data):
    # Extract unique fiscal years from raw data
    return sorted(set(row['fiscal_year'] for row in raw_data))

def get_columns(fiscal_years):
    # Build the columns dynamically based on unique fiscal years
    columns = [_("Party") + ":Link/Supplier:120", _("Account") + ":Link/Account:120"]
    columns.extend(_(year) + ":Currency:100" for year in fiscal_years)
    return columns

def get_data(filters):
    gl_entry = frappe.qb.DocType("GL Entry")
    return (
        frappe.qb.from_(gl_entry)
        .select(
            gl_entry.party,
            gl_entry.account,
            gl_entry.fiscal_year,
            (Sum(gl_entry.debit - gl_entry.credit) * -1).as_("balance"),
        )
        .where(
            (gl_entry.party_type == "Supplier")
            & (gl_entry.is_cancelled == 0)
            & gl_entry.posting_date.between(filters["from_date"], filters["to_date"])
            & (gl_entry.company == filters["company"])
        )
        .groupby(gl_entry.party, gl_entry.account, gl_entry.fiscal_year)
    ).run(as_dict=True)

def build_data(raw_data, fiscal_years):
    # Initialize a dictionary to store balances by party, account, and fiscal year
    data_dict = {}
    
    # Populate the dictionary with balances
    for row in raw_data:
        party = row['party']
        account = row['account']
        fiscal_year = row['fiscal_year']
        balance = row['balance']
        
        if (party, account) not in data_dict:
            data_dict[(party, account)] = {fy: 0 for fy in fiscal_years}
        
        data_dict[(party, account)][fiscal_year] = balance
    
    # Convert the dictionary to a list of lists for the report
    data = []
    for (party, account), balances in data_dict.items():
        row = [party, account]
        row.extend(balances[fiscal_year] for fiscal_year in fiscal_years)
        data.append(row)
    
    return data
