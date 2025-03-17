# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum


def execute(filters=None):
    if not filters:
        return [], []
    
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data


def get_columns():
    return [
        {
            "fieldname": "asset",
            "label": _("Asset"),
            "fieldtype": "Link",
            "options": "Asset",
            "width": 120
        },
        {
            "fieldname": "asset_name",
            "label": _("Asset Name"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "asset_category",
            "label": _("Asset Category"),
            "fieldtype": "Link",
            "options": "Asset Category",
            "width": 120
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "purchase_date",
            "label": _("Purchase Date"),
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname": "opening_wdv",
            "label": _("Opening WDV"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "depreciation_amount",
            "label": _("Depreciation Amount"),
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "fieldname": "depreciation_date",
            "label": _("Depreciation Date"),
            "fieldtype": "Date",
            "width": 140
        },
        {
            "fieldname": "depreciation_entry",
            "label": _("Depreciation Entry"),
            "fieldtype": "Link",
            "options": "Journal Entry",
            "width": 140
        },
        {
            "fieldname": "total_accumulated_depreciation",
            "label": _("Current Period Depreciation"),
            "fieldtype": "Currency",
            "width": 180
        },
        {
            "fieldname": "closing_wdv",
            "label": _("Closing WDV"),
            "fieldtype": "Currency",
            "width": 120
        },

        {
            "fieldname": "rate_of_depreciation",
            "label": _("Rate of Depreciation"),
            "fieldtype": "Percent",
            "width": 150
        }
    ]


def get_data(filters):
    data = []

    # Fetch depreciation accounts using QB
    Account = DocType("Account")
    depreciation_accounts = (
        frappe.qb.from_(Account)
        .select(Account.name)
        .where(Account.account_type == "Depreciation")
        .run(pluck=True)
    )

    if not depreciation_accounts:
        return data

    # Base filters for GL Entry
    filters_data = {
        "company": filters.get("company"),
        "posting_date": ["between", [filters.get("from_date"), filters.get("to_date")]],
        "against_voucher_type": "Asset",
        "account": ["in", depreciation_accounts],
        "is_cancelled": 0,
    }

    # Add asset filter if provided
    if filters.get("asset"):
        filters_data["against_voucher"] = filters.get("asset")

    # Fetch assets based on asset category using QB
    if filters.get("asset_category"):
        Asset = DocType("Asset")
        assets = (
            frappe.qb.from_(Asset)
            .select(Asset.name)
            .where(
                (Asset.asset_category == filters.get("asset_category"))
                & (Asset.docstatus == 1)
            )
            .run(pluck=True)
        )
        filters_data["against_voucher"] = ["in", assets]

    # Fetch GL Entries using QB
    GLEntry = DocType("GL Entry")
    gl_entries = (
        frappe.qb.from_(GLEntry)
        .select(
            GLEntry.against_voucher,
            GLEntry.debit_in_account_currency.as_("depreciation_amount"),
            GLEntry.voucher_no,
            GLEntry.posting_date,
        )
        .where(
            (GLEntry.company == filters.get("company"))
            & (GLEntry.posting_date[filters.get("from_date") : filters.get("to_date")])
            & (GLEntry.against_voucher_type == "Asset")
            & (GLEntry.account.isin(depreciation_accounts))
            & (GLEntry.is_cancelled == 0)
        )
        .orderby(GLEntry.against_voucher, GLEntry.posting_date)
        .run(as_dict=True)
    )

    if not gl_entries:
        return data

    # Get unique assets from GL Entries
    assets = list(set(d["against_voucher"] for d in gl_entries))

    # Fetch asset details using QB
    assets_details = get_assets_details(assets, filters)

    # Process GL Entries
    for d in gl_entries:
        asset_data = assets_details.get(d["against_voucher"])
        if asset_data:
            if not asset_data.get("accumulated_depreciation_amount"):
                asset_data["accumulated_depreciation_amount"] = 0

            # Calculate opening WDV
            asset_data["opening_wdv"] = (
                asset_data["gross_purchase_amount"]
                - asset_data["accumulated_depreciation_amount"]
            )

            # Increment accumulated depreciation
            asset_data["accumulated_depreciation_amount"] += d["depreciation_amount"]

            # Rename the key after incrementing
            asset_data["total_accumulated_depreciation"] = asset_data.pop("accumulated_depreciation_amount")

            # Calculate closing WDV
            asset_data["closing_wdv"] = (
                asset_data["gross_purchase_amount"]
                - asset_data["total_accumulated_depreciation"]
            )

            # Prepare the row for the report
            row = asset_data.copy()
            row.update(
                {
                    "depreciation_amount": d["depreciation_amount"],
                    "depreciation_date": d["posting_date"],
                    "depreciation_entry": d["voucher_no"],
                }
            )

            # Append the row to the data list
            data.append(row)

    return data


def get_assets_details(assets, filters):
    assets_details = {}

    # Fetch asset details using QB
    Asset = DocType("Asset")
    AssetFinanceBook = DocType("Asset Finance Book")

    assets_data = (
        frappe.qb.from_(Asset)
        .left_join(AssetFinanceBook)
        .on(Asset.name == AssetFinanceBook.parent)
        .select(
            Asset.name.as_("asset"),
            Asset.asset_name,
            Asset.gross_purchase_amount,
            Asset.asset_category,
            Asset.status,
            Asset.purchase_date,
            Asset.cost_center,
            AssetFinanceBook.rate_of_depreciation,
        )
        .where(Asset.name.isin(assets))
        .run(as_dict=True)
    )

    for asset in assets_data:
        assets_details[asset["asset"]] = asset
        
        if not asset.get("rate_of_depreciation"):
            asset["rate_of_depreciation"] = 0

    return assets_details