import frappe
from frappe import _

def execute(filters=None):
    columns, data = get_columns(), get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Asset ID"), "fieldname": "asset", "fieldtype": "Link", "options": "Asset", "width": 120},
        {"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 180},
        {"label": _("Depreciation Date"), "fieldname": "depreciation_date", "fieldtype": "Date", "width": 120},
        {"label": _("Depreciation Rate (%)"), "fieldname": "depreciation_rate", "fieldtype": "Float", "width": 120},
        {"label": _("Opening WDV"), "fieldname": "opening_wdv", "fieldtype": "Currency", "width": 140},
        {"label": _("Current Period Depreciation"), "fieldname": "depreciation_amount", "fieldtype": "Currency", "width": 160},
        {"label": _("Closing WDV"), "fieldname": "closing_wdv", "fieldtype": "Currency", "width": 140},
        {"label": _("Depreciation Entry"), "fieldname": "depreciation_entry", "fieldtype": "Link", "options": "Journal Entry", "width": 140},
        {"label": _("Asset Category"), "fieldname": "asset_category", "fieldtype": "Link", "options": "Asset Category", "width": 120},
        {"label": _("Current Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": _("Purchase Date"), "fieldname": "purchase_date", "fieldtype": "Date", "width": 120},
    ]

def get_data(filters):
    data = []
    depreciation_accounts = frappe.db.sql_list(
        """select name from tabAccount
        where ifnull(account_type, '') = 'Depreciation' """
    )

    filters_data = [
        ["company", "=", filters.get("company")],
        ["posting_date", ">=", filters.get("from_date")],
        ["posting_date", "<=", filters.get("to_date")],
        ["against_voucher_type", "=", "Asset"],
        ["account", "in", depreciation_accounts],
        ["is_cancelled", "=", 0],
    ]

    if filters.get("asset"):
        filters_data.append(["against_voucher", "=", filters.get("asset")])

    if filters.get("asset_category"):
        assets = frappe.db.sql_list(
            """select name from tabAsset
            where asset_category = %s and docstatus=1""",
            filters.get("asset_category"),
        )
        filters_data.append(["against_voucher", "in", assets])

    gl_entries = frappe.get_all(
        "GL Entry",
        filters=filters_data,
        fields=[
            "against_voucher", "debit_in_account_currency as depreciation_amount",
            "voucher_no", "posting_date"
        ],
        order_by="against_voucher, posting_date",
    )

    if not gl_entries:
        return data

    assets = [d.against_voucher for d in gl_entries]
    assets_details = get_assets_details(assets, filters)

    for d in gl_entries:
        asset_data = assets_details.get(d.against_voucher)
        if asset_data:
            if not asset_data.get("accumulated_depreciation_amount"):
                asset_data.accumulated_depreciation_amount = 0

            asset_data.opening_wdv = (
                asset_data.gross_purchase_amount - asset_data.accumulated_depreciation_amount
            )

            asset_data.accumulated_depreciation_amount += d.depreciation_amount
            asset_data.closing_wdv = (
                asset_data.gross_purchase_amount - asset_data.accumulated_depreciation_amount
            )

            row = frappe._dict(asset_data)
            row.update(
                {
                    "depreciation_amount": d.depreciation_amount,
                    "depreciation_date": d.posting_date,
                    "depreciation_entry": d.voucher_no,
                }
            )

            data.append(row)
    
    return data

def get_assets_details(assets, filters):
    assets_details = {}
    fields = [
        "name as asset", "asset_name", "gross_purchase_amount",
        "asset_category", "status", "purchase_date", "cost_center"
    ]

    # Fetch asset details
    for d in frappe.get_all("Asset", fields=fields, filters={"name": ("in", assets)}):
        assets_details.setdefault(d.asset, d)

    # Fetch rate_of_depreciation from Asset Depreciation Schedule
    depreciation_rates = frappe.get_all(
        "Asset Depreciation Schedule",
        filters={"asset": ("in", assets)},
        fields=["asset", "rate_of_depreciation"]
    )


    for d in depreciation_rates:
        if d.asset in assets_details:
            assets_details[d.asset].rate_of_depreciation = d.rate_of_depreciation

    return assets_details
