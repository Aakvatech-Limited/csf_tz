# CSF TZ navigation (Frappe 16.50+)

The Apps screen opens the existing **Tanzania** workspace. The app dock offers all eight shipped modules; each has a curated native Sidebar and a landing workspace. Finance, payroll, and administration have additional workspaces within CSF TZ. Open a module, use its shortcuts for frequent work, and expand report cards for the full catalogue.

| Dock entry / module | Landing workspace | Purpose |
|---|---|---|
| CSF TZ | Tanzania | Operations, masters, reports and settings shipped for this module |
| Purchase And Stock Management | CSF TZ Purchase and Stock | Operations, masters, reports and settings shipped for this module |
| Sales And Marketing | CSF TZ Sales and Marketing | Operations, masters, reports and settings shipped for this module |
| Meal Count | CSF TZ Meal Count | Operations, masters, reports and settings shipped for this module |
| Stanbic | CSF TZ Stanbic Banking | Operations, masters, reports and settings shipped for this module |
| KCB | CSF TZ KCB Banking | Operations, masters, reports and settings shipped for this module |
| VFD Providers | CSF TZ VFD Providers | Operations, masters, reports and settings shipped for this module |
| VFD Settings | CSF TZ VFD Setup | Operations, masters, reports and settings shipped for this module |

## Installation and migration

These are repository-authored standard JSON records checked against upstream Frappe version-16 source, not records exported or tested on a running site. They use the native Sidebar and Dock models introduced in Frappe 16.50. Deploy this branch to a Frappe 16.50+ development site, run `bench --site <site> migrate`, clear the site cache, then reload Desk. The existing `/desk/tanzania` app route and Tanzania workspace identity remain available. No navigation fixture or migration hook resets site/user arrangements.

Existing dock customizations can keep new entries hidden. A user can enable them in Manage Dock; site-wide changes require Workspace Manager. There are no legacy sidebar fixtures to convert. Rollback by reverting the navigation commit and migrating; check stale standard record cleanup on the site's installed Frappe revision.

## Access and dependencies

Navigation grants no permissions. Operators see links allowed by their DocType, report, page, and domain permissions; team leads see their existing manager-role access. System Managers additionally see the restricted CSF TZ Administration, bank initiation, and VFD setup workspaces. Many app-owned records are currently System Manager-only, including bank initiation, biometric setup, vehicle compliance, and provider configuration. CSF TZ Settings already grants read access to All; this change does not change that policy.

Payroll targets require HRMS on the site. Loan reports additionally require their existing Loan/Staff Loan dependencies. The framework hides inaccessible targets; validate optional-app installations and report execution separately. Some existing reports grant broad roles such as All or Employee; this navigation change does not audit or widen those permissions. Job Cards retains its existing Manufacturing domain restriction. The QR scanner records meal biometric logs.

No Dashboard, Dashboard Chart, or Number Card exports were found in this branch; no new KPIs are fabricated. Report availability does not establish correctness of an existing report's calculations or legacy integrations.

## Development-site acceptance

Repository validation passed: all 217 workspace/sidebar targets resolve against app exports or upstream Frappe/ERPNext/HRMS DocType paths; all 136 app candidates are included or explicitly excluded. Native schemas, Select values, module export paths, dock coverage, card counts, shortcut references, duplicate links, and diagnostic workspace roles were checked. Full repository pre-commit passed using the CI skip list (`frappe-semgrep-rules,full-repository-check`); Ruff also normalized formatting in two existing test files. Bench migration, functional report execution, and user-role/browser checks remain unperformed because no running Frappe site is available here.

- Migrate and confirm eight module Sidebar records, one app Dock, and eleven standard Workspaces.
- Open CSF TZ from Apps, then each dock entry. Confirm each lands on its Home workspace.
- As an Accounts User, check tax/finance access; as Accounts Manager, check manager reports and import settings.
- As HR User/HR Manager on an HRMS site, check payroll operations and statutory reports.
- As Stock User/Sales User, check purchasing and sales reports; restricted records should remain unavailable.
- As System Manager, check diagnostics, banking settings, biometric masters, vehicle compliance, and VFD setup.
- Check Manufacturing Job Cards visibility only with the active domain and allowed roles.
- Change a user's sidebar/dock arrangement, migrate again, and verify the customization remains.
- Check a site without optional HRMS/loan apps for hidden unresolved targets.
- Check all cards and shortcuts, ordinary-user discoverability, and narrow-screen layout.

## Complete discovery and coverage matrix

Every shipped DocType, Report and Page was considered. Child tables, the test DocType, the item counter and alert helper are deliberately excluded. All remaining app targets appear in a workspace; curated sidebars expose frequent tasks and links to full catalogues. Diagnostics are isolated in a System Manager workspace. Source modules with legacy `csf_tz` spelling are recorded verbatim.

| Source module | Type | Target | Status | Workspace or exclusion reason | Existing roles | Source |
|---|---|---|---|---|---|---|
| Sales And Marketing | DocType | Allert Custom | Excluded | Internal alert helper with only a name field | System Manager | `csf_tz/sales_and_marketing/doctype/allert_custom/allert_custom.json` |
| CSF TZ | DocType | Authority Notification Role | Excluded | Embedded child table; navigate through its parent document | Framework/ref-DocType access | `csf_tz/csf_tz/doctype/authority_notification_role/authority_notification_role.json` |
| CSF TZ | DocType | Bank Charges Pattern | Included | CSF TZ Finance | System Manager | `csf_tz/csf_tz/doctype/bank_charges_pattern/bank_charges_pattern.json` |
| Purchase And Stock Management | DocType | Bin List | Excluded | Embedded child table; navigate through its parent document | Framework/ref-DocType access | `csf_tz/purchase_and_stock_management/doctype/bin_list/bin_list.json` |
| Purchase And Stock Management | DocType | Bin Setup | Included | CSF TZ Purchase and Stock | System Manager | `csf_tz/purchase_and_stock_management/doctype/bin_setup/bin_setup.json` |
| CSF TZ | DocType | CSF API Response Log | Administration only | CSF TZ Administration | System Manager | `csf_tz/csf_tz/doctype/csf_api_response_log/csf_api_response_log.json` |
| CSF TZ | DocType | CSF TZ Bank Charges | Included | CSF TZ Finance | System Manager | `csf_tz/csf_tz/doctype/csf_tz_bank_charges/csf_tz_bank_charges.json` |
| CSF TZ | DocType | CSF TZ Bank Charges Detail | Excluded | Embedded child table; navigate through its parent document | Framework/ref-DocType access | `csf_tz/csf_tz/doctype/csf_tz_bank_charges_detail/csf_tz_bank_charges_detail.json` |
| Meal Count | DocType | CSF TZ Biometric Device | Included | CSF TZ Meal Count | System Manager | `csf_tz/meal_count/doctype/csf_tz_biometric_device/csf_tz_biometric_device.json` |
| Meal Count | DocType | CSF TZ Biometric Log | Included | CSF TZ Meal Count | System Manager | `csf_tz/meal_count/doctype/csf_tz_biometric_log/csf_tz_biometric_log.json` |
| Meal Count | DocType | CSF TZ Biometric User | Included | CSF TZ Meal Count | System Manager | `csf_tz/meal_count/doctype/csf_tz_biometric_user/csf_tz_biometric_user.json` |
| Meal Count | DocType | CSF TZ Biometric User Type | Included | CSF TZ Meal Count | System Manager | `csf_tz/meal_count/doctype/csf_tz_biometric_user_type/csf_tz_biometric_user_type.json` |
| Meal Count | DocType | CSF TZ Meal Type | Included | CSF TZ Meal Count | System Manager | `csf_tz/meal_count/doctype/csf_tz_meal_type/csf_tz_meal_type.json` |
| CSF TZ | DocType | CSF TZ Settings | Included | Tanzania | System Manager, All | `csf_tz/csf_tz/doctype/csf_tz_settings/csf_tz_settings.json` |
| Sales And Marketing | DocType | Communications | Included | CSF TZ Sales and Marketing | System Manager, Sales User | `csf_tz/sales_and_marketing/doctype/communications/communications.json` |
| VFD Settings | DocType | Company VFD Provider | Included | CSF TZ VFD Setup | System Manager | `csf_tz/vfd_settings/doctype/company_vfd_provider/company_vfd_provider.json` |
| Sales And Marketing | DocType | Customer Item | Excluded | Embedded child table; navigate through its parent document | Framework/ref-DocType access | `csf_tz/sales_and_marketing/doctype/customer_item/customer_item.json` |
| VFD Providers | DocType | DIRM VFD Settings | Included | CSF TZ VFD Providers | System Manager, System Manager | `csf_tz/vfd_providers/doctype/dirm_vfd_settings/dirm_vfd_settings.json` |
| CSF TZ | DocType | EFD Z Report | Included | Tanzania | System Manager | `csf_tz/csf_tz/doctype/efd_z_report/efd_z_report.json` |
| CSF TZ | DocType | EFD Z Report Invoice | Excluded | Embedded child table; navigate through its parent document | Framework/ref-DocType access | `csf_tz/csf_tz/doctype/efd_z_report_invoice/efd_z_report_invoice.json` |
| CSF TZ | DocType | Electronic Fiscal Device | Included | Tanzania | System Manager | `csf_tz/csf_tz/doctype/electronic_fiscal_device/electronic_fiscal_device.json` |
| CSF TZ | DocType | Foreign Import Exchange Difference Details | Excluded | Embedded child table; navigate through its parent document | Framework/ref-DocType access | `csf_tz/csf_tz/doctype/foreign_import_exchange_difference_details/foreign_import_exchange_difference_details.json` |
| CSF TZ | DocType | Foreign Import LCV Details | Excluded | Embedded child table; navigate through its parent document | Framework/ref-DocType access | `csf_tz/csf_tz/doctype/foreign_import_lcv_details/foreign_import_lcv_details.json` |
| CSF TZ | DocType | Foreign Import Payment Details | Excluded | Embedded child table; navigate through its parent document | Framework/ref-DocType access | `csf_tz/csf_tz/doctype/foreign_import_payment_details/foreign_import_payment_details.json` |
| CSF TZ | DocType | Foreign Import Settings | Included | CSF TZ Finance | System Manager, Accounts Manager | `csf_tz/csf_tz/doctype/foreign_import_settings/foreign_import_settings.json` |
| CSF TZ | DocType | Foreign Import Transaction | Included | CSF TZ Finance | System Manager, Accounts Manager, Accounts User | `csf_tz/csf_tz/doctype/foreign_import_transaction/foreign_import_transaction.json` |
| Purchase And Stock Management | DocType | Item Number | Excluded | Internal item numbering counter | System Manager | `csf_tz/purchase_and_stock_management/doctype/item_number/item_number.json` |
| KCB | DocType | KCB Payments Initiation | Included | CSF TZ KCB Banking | System Manager | `csf_tz/kcb/doctype/kcb_payments_initiation/kcb_payments_initiation.json` |
| KCB | DocType | KCB Payments Initiation Info | Excluded | Embedded child table; navigate through its parent document | Framework/ref-DocType access | `csf_tz/kcb/doctype/kcb_payments_initiation_info/kcb_payments_initiation_info.json` |
| KCB | DocType | KCB Settings | Included | CSF TZ KCB Banking | System Manager | `csf_tz/kcb/doctype/kcb_settings/kcb_settings.json` |
| CSF TZ | DocType | Latra Licenses | Included | Tanzania | System Manager | `csf_tz/csf_tz/doctype/latra_licenses/latra_licenses.json` |
| CSF TZ | DocType | Latra Offence | Included | Tanzania | System Manager | `csf_tz/csf_tz/doctype/latra_offence/latra_offence.json` |
| CSF TZ | DocType | Latra Settings | Included | Tanzania | System Manager | `csf_tz/csf_tz/doctype/latra_settings/latra_settings.json` |
| Sales And Marketing | DocType | Marketing Dept | Included | CSF TZ Sales and Marketing | System Manager | `csf_tz/sales_and_marketing/doctype/marketing_dept/marketing_dept.json` |
| Purchase And Stock Management | DocType | Order Track | Included | CSF TZ Purchase and Stock | System Manager | `csf_tz/purchase_and_stock_management/doctype/order_track/order_track.json` |
| Purchase And Stock Management | DocType | Order Tracking Container | Excluded | Embedded child table; navigate through its parent document | Framework/ref-DocType access | `csf_tz/purchase_and_stock_management/doctype/order_tracking_container/order_tracking_container.json` |
| Sales And Marketing | DocType | Past Sales | Included | CSF TZ Sales and Marketing | System Manager | `csf_tz/sales_and_marketing/doctype/past_sales/past_sales.json` |
| Sales And Marketing | DocType | Past Serial No | Included | CSF TZ Sales and Marketing | System Manager | `csf_tz/sales_and_marketing/doctype/past_serial_no/past_serial_no.json` |
| Sales And Marketing | DocType | Payment Plan | Excluded | Embedded child table; navigate through its parent document | Framework/ref-DocType access | `csf_tz/sales_and_marketing/doctype/payment_plan/payment_plan.json` |
| Sales And Marketing | DocType | Products of Interest | Excluded | Embedded child table; navigate through its parent document | Framework/ref-DocType access | `csf_tz/sales_and_marketing/doctype/products_of_interest/products_of_interest.json` |
| Purchase And Stock Management | DocType | Purchase And Stock Management Test | Excluded | Test-only DocType | System Manager | `csf_tz/purchase_and_stock_management/doctype/purchase_and_stock_management_test/purchase_and_stock_management_test.json` |
| VFD Providers | DocType | Simplify VFD Settings | Included | CSF TZ VFD Providers | System Manager, System Manager | `csf_tz/vfd_providers/doctype/simplify_vfd_settings/simplify_vfd_settings.json` |
| Stanbic | DocType | Stanbic Payments Info | Excluded | Embedded child table; navigate through its parent document | Framework/ref-DocType access | `csf_tz/stanbic/doctype/stanbic_payments_info/stanbic_payments_info.json` |
| Stanbic | DocType | Stanbic Payments Initiation | Included | CSF TZ Stanbic Banking | System Manager | `csf_tz/stanbic/doctype/stanbic_payments_initiation/stanbic_payments_initiation.json` |
| Stanbic | DocType | Stanbic Setting | Included | CSF TZ Stanbic Banking | System Manager | `csf_tz/stanbic/doctype/stanbic_setting/stanbic_setting.json` |
| CSF TZ | DocType | TRA TAX Inv | Included | Tanzania | System Manager, Accounts Manager, Accounts User | `csf_tz/csf_tz/doctype/tra_tax_inv/tra_tax_inv.json` |
| CSF TZ | DocType | TRA TAX Inv Item | Excluded | Embedded child table; navigate through its parent document | Framework/ref-DocType access | `csf_tz/csf_tz/doctype/tra_tax_inv_item/tra_tax_inv_item.json` |
| CSF TZ | DocType | TZ District | Included | Tanzania | System Manager | `csf_tz/csf_tz/doctype/tz_district/tz_district.json` |
| CSF TZ | DocType | TZ Insurance Company Detail | Excluded | Embedded child table; navigate through its parent document | Framework/ref-DocType access | `csf_tz/csf_tz/doctype/tz_insurance_company_detail/tz_insurance_company_detail.json` |
| CSF TZ | DocType | TZ Insurance Cover Note | Included | Tanzania | System Manager | `csf_tz/csf_tz/doctype/tz_insurance_cover_note/tz_insurance_cover_note.json` |
| CSF TZ | DocType | TZ Insurance Policy Holder Detail | Excluded | Embedded child table; navigate through its parent document | Framework/ref-DocType access | `csf_tz/csf_tz/doctype/tz_insurance_policy_holder_detail/tz_insurance_policy_holder_detail.json` |
| CSF TZ | DocType | TZ Insurance Vehicle Detail | Excluded | Embedded child table; navigate through its parent document | Framework/ref-DocType access | `csf_tz/csf_tz/doctype/tz_insurance_vehicle_detail/tz_insurance_vehicle_detail.json` |
| CSF TZ | DocType | TZ Region | Included | Tanzania | System Manager | `csf_tz/csf_tz/doctype/tz_region/tz_region.json` |
| CSF TZ | DocType | TZ Village | Included | Tanzania | System Manager | `csf_tz/csf_tz/doctype/tz_village/tz_village.json` |
| CSF TZ | DocType | TZ Ward | Included | Tanzania | System Manager | `csf_tz/csf_tz/doctype/tz_ward/tz_ward.json` |
| VFD Providers | DocType | Total VFD Setting | Included | CSF TZ VFD Providers | System Manager, System Manager | `csf_tz/vfd_providers/doctype/total_vfd_setting/total_vfd_setting.json` |
| VFD Providers | DocType | VFD Provider | Included | CSF TZ VFD Providers | System Manager | `csf_tz/vfd_providers/doctype/vfd_provider/vfd_provider.json` |
| VFD Providers | DocType | VFD Provider Attribute | Excluded | Embedded child table; navigate through its parent document | Framework/ref-DocType access | `csf_tz/vfd_providers/doctype/vfd_provider_attribute/vfd_provider_attribute.json` |
| VFD Providers | DocType | VFD Provider Posting | Included | CSF TZ VFD Providers | System Manager | `csf_tz/vfd_providers/doctype/vfd_provider_posting/vfd_provider_posting.json` |
| VFD Providers | DocType | VFDPlus Settings | Included | CSF TZ VFD Providers | System Manager, System Manager | `csf_tz/vfd_providers/doctype/vfdplus_settings/vfdplus_settings.json` |
| CSF TZ | DocType | Vehicle Fine Record | Included | Tanzania | System Manager | `csf_tz/csf_tz/doctype/vehicle_fine_record/vehicle_fine_record.json` |
| CSF TZ | DocType | Vehicle Sync Task | Administration only | CSF TZ Administration | System Manager | `csf_tz/csf_tz/doctype/vehicle_sync_task/vehicle_sync_task.json` |
| CSF TZ | Page | jobcards | Included | CSF TZ Purchase and Stock | Manufacturing User, Manufacturing Manager, System Manager, Cab Line Team Leader, Body Shop Team Leader, Production Team Leader, Production Manager, KD Engineer | `csf_tz/csf_tz/page/jobcards/jobcards.json` |
| CSF TZ | Page | scan-qrcode | Included | CSF TZ Meal Count | Framework/ref-DocType access | `csf_tz/csf_tz/page/scan_qrcode/scan_qrcode.json` |
| CSF TZ | Report | AV Sales Invoice Trend | Included | CSF TZ Sales and Marketing | Accounts Manager, Accounts User, Employee Self Service | `csf_tz/csf_tz/report/av_sales_invoice_trend/av_sales_invoice_trend.json` |
| CSF TZ | Report | Accounts Receivable Multi Currency | Included | CSF TZ Finance | Accounts Manager, Accounts User | `csf_tz/csf_tz/report/accounts_receivable_multi_currency/accounts_receivable_multi_currency.json` |
| CSF TZ | Report | Accounts Receivable Summary Multi Currency | Included | CSF TZ Finance | Accounts Manager, Accounts User | `csf_tz/csf_tz/report/accounts_receivable_summary_multi_currency/accounts_receivable_summary_multi_currency.json` |
| CSF TZ | Report | Balance below Safety Stock | Included | CSF TZ Purchase and Stock | Sales User, Purchase User, Stock User | `csf_tz/csf_tz/report/balance_below_safety_stock/balance_below_safety_stock.json` |
| CSF TZ | Report | Bank Ledger Summary | Included | CSF TZ Finance | Accounts User, Accounts Manager, Auditor | `csf_tz/csf_tz/report/bank_ledger_summary/bank_ledger_summary.json` |
| CSF TZ | Report | Bank Report | Included | CSF TZ Finance | System Manager, Accounts Manager, HR Manager | `csf_tz/csf_tz/report/bank_report/bank_report.json` |
| csf_tz | Report | Bank Trans vs GL Entry Report | Included | CSF TZ Finance | System Manager, Accounts Manager, Accounts User | `csf_tz/csf_tz/report/bank_trans_vs_gl_entry_report/bank_trans_vs_gl_entry_report.json` |
| CSF TZ | Report | Bank Transaction Summary | Included | CSF TZ Finance | System Manager, Accounts Manager, Accounts User | `csf_tz/csf_tz/report/bank_transaction_summary/bank_transaction_summary.json` |
| Purchase And Stock Management | Report | Bin System | Included | CSF TZ Purchase and Stock | Sales User, Purchase User, Stock User | `csf_tz/purchase_and_stock_management/report/bin_system/bin_system.json` |
| Sales And Marketing | Report | Brand Sales Report | Included | CSF TZ Sales and Marketing | Accounts Manager, Accounts User | `csf_tz/sales_and_marketing/report/brand_sales_report/brand_sales_report.json` |
| CSF TZ | Report | CSF TZ Stock Movement | Included | CSF TZ Purchase and Stock | Stock User, Accounts Manager | `csf_tz/csf_tz/report/csf_tz_stock_movement/csf_tz_stock_movement.json` |
| CSF TZ | Report | Credit Note List | Included | CSF TZ Sales and Marketing | Accounts Manager, Accounts User | `csf_tz/csf_tz/report/credit_note_list/credit_note_list.json` |
| Sales And Marketing | Report | Customer Loan Assistance report | Included | CSF TZ Sales and Marketing | Framework/ref-DocType access | `csf_tz/sales_and_marketing/report/customer_loan_assistance_report/customer_loan_assistance_report.json` |
| CSF TZ | Report | Employee Salary Register with Monthly Comparison | Included | Tanzania Payroll | Accounts Manager | `csf_tz/csf_tz/report/employee_salary_register_with_monthly_comparison/employee_salary_register_with_monthly_comparison.json` |
| CSF TZ | Report | Excise Duty Detailed Report | Included | Tanzania | Framework/ref-DocType access | `csf_tz/csf_tz/report/excise_duty_detailed_report/excise_duty_detailed_report.json` |
| CSF TZ | Report | Excise Duty Report | Included | Tanzania | Framework/ref-DocType access | `csf_tz/csf_tz/report/excise_duty_report/excise_duty_report.json` |
| CSF TZ | Report | Excise Duty Stock | Included | Tanzania | Stock User, Accounts Manager | `csf_tz/csf_tz/report/excise_duty_stock/excise_duty_stock.json` |
| CSF TZ | Report | GL Entry Summary for Trading Account | Included | CSF TZ Purchase and Stock | Stock User, Accounts Manager | `csf_tz/csf_tz/report/gl_entry_summary_for_trading_account/gl_entry_summary_for_trading_account.json` |
| CSF TZ | Report | General Ledger Pro | Included | CSF TZ Finance | Accounts User, Accounts Manager, Auditor | `csf_tz/csf_tz/report/general_ledger_pro/general_ledger_pro.json` |
| CSF TZ | Report | Gross Profit Pro | Included | CSF TZ Sales and Marketing | Accounts Manager, Accounts User, Employee Self Service, System Manager, Purchase User, Auditor | `csf_tz/csf_tz/report/gross_profit_pro/gross_profit_pro.json` |
| CSF TZ | Report | HESLB Return online | Included | Tanzania Payroll | HR Manager, HR User, Employee, Leave Approver, All, Employee Self Service | `csf_tz/csf_tz/report/heslb_return_online/heslb_return_online.json` |
| CSF TZ | Report | ITX 230.01.E – Withholding Tax Statement | Included | Tanzania | System Manager | `csf_tz/csf_tz/report/itx_230.01.e_–_withholding_tax_statement/itx_230.01.e_–_withholding_tax_statement.json` |
| CSF TZ | Report | ITX.215.03.E SDL Monthly Returns | Included | Tanzania Payroll | HR Manager, HR User, Employee, Leave Approver, All, Employee Self Service | `csf_tz/csf_tz/report/itx.215.03.e_sdl_monthly_returns/itx.215.03.e_sdl_monthly_returns.json` |
| CSF TZ | Report | ITX.219.03.E Statement of Tax Withheld | Included | Tanzania Payroll | HR Manager, Accounts Manager | `csf_tz/csf_tz/report/itx.219.03.e_statement_of_tax_withheld/itx.219.03.e_statement_of_tax_withheld.json` |
| CSF TZ | Report | Import Exchange Differences | Included | CSF TZ Finance | System Manager, Accounts Manager, Accounts User | `csf_tz/csf_tz/report/import_exchange_differences/import_exchange_differences.json` |
| Sales And Marketing | Report | Item Wise Leads Report | Included | CSF TZ Sales and Marketing | Sales Manager, System Manager, Sales User, Sales Executive, Branch In Charge, Stock Supervisor | `csf_tz/sales_and_marketing/report/item_wise_leads_report/item_wise_leads_report.json` |
| Sales And Marketing | Report | Items Marked For Delivery | Included | CSF TZ Sales and Marketing | Accounts Manager, Accounts User | `csf_tz/sales_and_marketing/report/items_marked_for_delivery/items_marked_for_delivery.json` |
| CSF TZ | Report | Itemwise Stock Movement | Included | CSF TZ Purchase and Stock | Stock Manager, Accounts Manager | `csf_tz/csf_tz/report/itemwise_stock_movement/itemwise_stock_movement.json` |
| CSF TZ | Report | Loan Outstanding | Included | Tanzania Payroll | System Manager, Loan Manager | `csf_tz/csf_tz/report/loan_outstanding/loan_outstanding.json` |
| CSF TZ | Report | Loan Repayment Details | Included | Tanzania Payroll | HR Manager, Employee, HR User, HR Manager (Group), Directorate | `csf_tz/csf_tz/report/loan_repayment_details/loan_repayment_details.json` |
| CSF TZ | Report | Monthly Account Balance | Included | CSF TZ Finance | Accounts Manager, Auditor, Accounts User, System Manager, Tax Invoice User | `csf_tz/csf_tz/report/monthly_account_balance/monthly_account_balance.json` |
| CSF TZ | Report | Monthly Purchase Summary | Included | CSF TZ Purchase and Stock | Accounts Manager | `csf_tz/csf_tz/report/monthly_purchase_summary/monthly_purchase_summary.json` |
| CSF TZ | Report | Monthly Sales Summary | Included | CSF TZ Sales and Marketing | Accounts Manager | `csf_tz/csf_tz/report/monthly_sales_summary/monthly_sales_summary.json` |
| CSF TZ | Report | Monthly Timesheet Report | Included | Tanzania Payroll | HR User, Projects User, Accounts User, Manufacturing User, Employee, Employee Self Service | `csf_tz/csf_tz/report/monthly_timesheet_report/monthly_timesheet_report.json` |
| CSF TZ | Report | Multi-Currency Ledger | Included | CSF TZ Finance | Accounts User, Accounts Manager, Auditor | `csf_tz/csf_tz/report/multi_currency_ledger/multi_currency_ledger.json` |
| CSF TZ | Report | NMB Bank Charges in Bank Transaction | Included | CSF TZ Finance | System Manager, Accounts Manager, Accounts User | `csf_tz/csf_tz/report/nmb_bank_charges_in_bank_transaction/nmb_bank_charges_in_bank_transaction.json` |
| CSF TZ | Report | NMB Bank Transaction not Bank Charges | Included | CSF TZ Finance | Framework/ref-DocType access | `csf_tz/csf_tz/report/nmb_bank_transaction_not_bank_charges/nmb_bank_transaction_not_bank_charges.json` |
| CSF TZ | Report | NSSF CON5 Monthly Contribution - Online Version | Included | Tanzania Payroll | HR Manager, HR User, Employee, Leave Approver, All, Employee Self Service | `csf_tz/csf_tz/report/nssf_con5_monthly_contribution___online_version/nssf_con5_monthly_contribution___online_version.json` |
| Purchase And Stock Management | Report | Ordered Items To Be Delivered | Included | CSF TZ Purchase and Stock | Stock User, Stock Manager, Sales User, Accounts User | `csf_tz/purchase_and_stock_management/report/ordered_items_to_be_delivered/ordered_items_to_be_delivered.json` |
| CSF TZ | Report | Output VAT Reconciliation | Included | Tanzania | System Manager, Accounts Manager | `csf_tz/csf_tz/report/output_vat_reconciliation/output_vat_reconciliation.json` |
| csf_tz | Report | PAYE Report Mapping | Included | Tanzania Payroll | Framework/ref-DocType access | `csf_tz/csf_tz/report/paye_report_mapping/paye_report_mapping.json` |
| CSF TZ | Report | Parent Child Relationship | Administration only | CSF TZ Administration | System Manager, Administrator | `csf_tz/csf_tz/report/parent_child_relationship/parent_child_relationship.json` |
| CSF TZ | Report | Particular Item History Report | Included | CSF TZ Purchase and Stock | Stock User, Sales User, Purchase User | `csf_tz/csf_tz/report/particular_item_history_report/particular_item_history_report.json` |
| CSF TZ | Report | Payroll for Mobile Payment | Included | Tanzania Payroll | HR Manager, Employee, HR User, System Manager, Employee Self Service | `csf_tz/csf_tz/report/payroll_for_mobile_payment/payroll_for_mobile_payment.json` |
| Purchase And Stock Management | Report | Pending Ordered Items | Included | CSF TZ Purchase and Stock | Stock Manager, Stock User, Purchase User, Accounts User | `csf_tz/purchase_and_stock_management/report/pending_ordered_items/pending_ordered_items.json` |
| Sales And Marketing | Report | Previous Ams Customer Report | Included | CSF TZ Sales and Marketing | System Manager, Sales Manager, Sales Master Manager, Accounts Manager, Accounts User, Parts Manager, After Sales Branch Manager, After Sales User | `csf_tz/sales_and_marketing/report/previous_ams_customer_report/previous_ams_customer_report.json` |
| Purchase And Stock Management | Report | Purchase History | Included | CSF TZ Purchase and Stock | Stock User, Purchase Manager, Purchase User | `csf_tz/purchase_and_stock_management/report/purchase_history/purchase_history.json` |
| Purchase And Stock Management | Report | Reordering Items | Included | CSF TZ Purchase and Stock | Stock User, Purchase Manager, Purchase User | `csf_tz/purchase_and_stock_management/report/reordering_items/reordering_items.json` |
| CSF TZ | Report | Role Permission Listing | Administration only | CSF TZ Administration | System Manager | `csf_tz/csf_tz/report/role_permission_listing/role_permission_listing.json` |
| CSF TZ | Report | Salary Register CTC | Included | Tanzania Payroll | Employee, HR Manager, HR User, HR Manager (Group), Directorate, Leave Approver, All, Employee Self Service | `csf_tz/csf_tz/report/salary_register_ctc/salary_register_ctc.json` |
| CSF TZ | Report | Salary Register Summary | Included | Tanzania Payroll | Employee, HR Manager, HR User, HR Manager (Group) | `csf_tz/csf_tz/report/salary_register_summary/salary_register_summary.json` |
| CSF TZ | Report | Salary Register Summary with Components | Included | Tanzania Payroll | Employee, HR Manager, HR User, HR Manager (Group) | `csf_tz/csf_tz/report/salary_register_summary_with_components/salary_register_summary_with_components.json` |
| CSF TZ | Report | Salary Register Summary with Monthly Comparison | Included | Tanzania Payroll | Employee, HR Manager, HR User, HR Manager (Group), Directorate, Leave Approver, All, Employee Self Service | `csf_tz/csf_tz/report/salary_register_summary_with_monthly_comparison/salary_register_summary_with_monthly_comparison.json` |
| CSF TZ | Report | Salary Register csf | Included | Tanzania Payroll | Employee, HR Manager, HR User, HR Manager (Group), Directorate | `csf_tz/csf_tz/report/salary_register_csf/salary_register_csf.json` |
| Sales And Marketing | Report | Sales Details Report | Included | CSF TZ Sales and Marketing | Accounts Manager, Accounts User, Sales Executive, Branch In Charge, Stock Supervisor | `csf_tz/sales_and_marketing/report/sales_details_report/sales_details_report.json` |
| Purchase And Stock Management | Report | Shipment Tracking | Included | CSF TZ Purchase and Stock | System Manager, Branch Stock Controller, Branch Service Controller, Branch In Charge | `csf_tz/purchase_and_stock_management/report/shipment_tracking/shipment_tracking.json` |
| Sales And Marketing | Report | Spare Sales Report | Included | CSF TZ Sales and Marketing | Accounts User, Accounts Manager, Sales User, System Manager, Parts Consultant | `csf_tz/sales_and_marketing/report/spare_sales_report/spare_sales_report.json` |
| CSF TZ | Report | Stock Balance Pro | Included | CSF TZ Purchase and Stock | Stock User, Accounts Manager | `csf_tz/csf_tz/report/stock_balance_pro/stock_balance_pro.json` |
| CSF TZ | Report | Stock Balance pivot warehouse | Included | CSF TZ Purchase and Stock | Stock User, Accounts Manager | `csf_tz/csf_tz/report/stock_balance_pivot_warehouse/stock_balance_pivot_warehouse.json` |
| CSF TZ | Report | Stock Ledger Summary for Trading Account | Included | CSF TZ Purchase and Stock | Stock User, Accounts Manager | `csf_tz/csf_tz/report/stock_ledger_summary_for_trading_account/stock_ledger_summary_for_trading_account.json` |
| CSF TZ | Report | Stock Ledger for Trading Account | Included | CSF TZ Purchase and Stock | Stock User, Accounts Manager | `csf_tz/csf_tz/report/stock_ledger_for_trading_account/stock_ledger_for_trading_account.json` |
| csf_tz | Report | Stock Reconciliation troubleshoot | Administration only | CSF TZ Administration | Stock Manager, System Manager | `csf_tz/csf_tz/report/stock_reconciliation_troubleshoot/stock_reconciliation_troubleshoot.json` |
| Purchase And Stock Management | Report | Supplier Contacts | Included | CSF TZ Purchase and Stock | Sales User, Purchase User, Maintenance User, Accounts User | `csf_tz/purchase_and_stock_management/report/supplier_contacts/supplier_contacts.json` |
| CSF TZ | Report | TRA Input VAT Returns eFiling | Included | Tanzania | Accounts User, Purchase User, Accounts Manager, Auditor | `csf_tz/csf_tz/report/tra_input_vat_returns_efiling/tra_input_vat_returns_efiling.json` |
| CSF TZ | Report | Trial Balance Report in USD | Included | CSF TZ Finance | Accounts User, Accounts Manager, Auditor | `csf_tz/csf_tz/report/trial_balance_report_in_usd/trial_balance_report_in_usd.json` |
| CSF TZ | Report | User Role Listing | Administration only | CSF TZ Administration | System Manager, Employee Self Service | `csf_tz/csf_tz/report/user_role_listing/user_role_listing.json` |
| CSF TZ | Report | VAT eFiling Returns | Included | Tanzania | Accounts Manager, Accounts User | `csf_tz/csf_tz/report/vat_efiling_returns/vat_efiling_returns.json` |
| CSF TZ | Report | WCF Employee | Included | Tanzania Payroll | HR User, HR Manager, Employee, Employee Self Service | `csf_tz/csf_tz/report/wcf_employee/wcf_employee.json` |
| CSF TZ | Report | Warehouse wise Item Balance and Value | Included | CSF TZ Purchase and Stock | Accounts Manager, Stock User, Stock Manager, Sales User | `csf_tz/csf_tz/report/warehouse_wise_item_balance_and_value/warehouse_wise_item_balance_and_value.json` |
| CSF TZ | Report | Withholding Tax Payment Summary | Included | Tanzania | Accounts User, Accounts Manager | `csf_tz/csf_tz/report/withholding_tax_payment_summary/withholding_tax_payment_summary.json` |
| CSF TZ | Report | Withholding Tax Summary on Sales | Included | Tanzania | Framework/ref-DocType access | `csf_tz/csf_tz/report/withholding_tax_summary_on_sales/withholding_tax_summary_on_sales.json` |
| CSF TZ | Report | Withholding Tax Upload | Included | Tanzania | Framework/ref-DocType access | `csf_tz/csf_tz/report/withholding_tax_upload/withholding_tax_upload.json` |
