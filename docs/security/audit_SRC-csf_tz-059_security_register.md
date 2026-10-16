# SRC-csf_tz-059 security finding register

Audit baseline: 56 security findings (43 SQL, 6 role permissions, 7 filesystem). Branch: version-16-hotfix; remediation PR #526. Original audit line numbers are preserved.

No item is closed until new Marketplace audit evidence and relevant regression tests confirm the fix. Query placeholders are bound values; static clauses and DocType fields are checked separately from user values.

| ID | Group | Original source | Code disposition | Verification |
|---|---|---|---|---|
| SEC-001 | SQL | `csf_tz/csf_tz/dashboard_chart_source/multi_account_balance_timeline/multi_account_balance_timeline.py:376` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-002 | SQL | `csf_tz/csf_tz/doctype/efd_z_report/efd_z_report.py:48` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-003 | SQL | `csf_tz/csf_tz/report/accounts_receivable_multi_currency/accounts_receivable_multi_currency.py:304` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-004 | SQL | `csf_tz/csf_tz/report/accounts_receivable_multi_currency/accounts_receivable_multi_currency.py:318` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-005 | SQL | `csf_tz/csf_tz/report/accounts_receivable_multi_currency/accounts_receivable_multi_currency.py:413` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-006 | SQL | `csf_tz/csf_tz/report/accounts_receivable_multi_currency/accounts_receivable_multi_currency.py:533` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-007 | SQL | `csf_tz/csf_tz/report/accounts_receivable_multi_currency/accounts_receivable_multi_currency.py:658` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-008 | SQL | `csf_tz/csf_tz/report/accounts_receivable_summary_multi_currency/accounts_receivable_utils.py:541` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-009 | SQL | `csf_tz/csf_tz/report/accounts_receivable_summary_multi_currency/accounts_receivable_utils.py:562` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-010 | SQL | `csf_tz/csf_tz/report/accounts_receivable_summary_multi_currency/accounts_receivable_utils.py:671` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-011 | SQL | `csf_tz/csf_tz/report/accounts_receivable_summary_multi_currency/accounts_receivable_utils.py:772` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-012 | SQL | `csf_tz/csf_tz/report/accounts_receivable_summary_multi_currency/accounts_receivable_utils.py:800` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-013 | SQL | `csf_tz/csf_tz/report/accounts_receivable_summary_multi_currency/accounts_receivable_utils.py:815` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-014 | SQL | `csf_tz/csf_tz/report/accounts_receivable_summary_multi_currency/accounts_receivable_utils.py:841` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-015 | SQL | `csf_tz/csf_tz/report/accounts_receivable_summary_multi_currency/accounts_receivable_utils.py:856` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-016 | SQL | `csf_tz/csf_tz/report/accounts_receivable_summary_multi_currency/accounts_receivable_utils.py:865` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-017 | SQL | `csf_tz/csf_tz/report/employee_salary_register_with_monthly_comparison/employee_salary_register_with_monthly_comparison.py:173` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-018 | SQL | `csf_tz/csf_tz/report/employee_salary_register_with_monthly_comparison/employee_salary_register_with_monthly_comparison.py:189` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-019 | SQL | `csf_tz/csf_tz/report/excise_duty_stock/excise_duty_stock.py:179` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-020 | SQL | `csf_tz/csf_tz/report/general_ledger_pro/general_ledger.py:145` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-021 | SQL | `csf_tz/csf_tz/report/general_ledger_pro/general_ledger_pro.py:204` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-022 | SQL | `csf_tz/csf_tz/report/general_ledger_pro/general_ledger_pro.py:239` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-023 | SQL | `csf_tz/csf_tz/report/gross_profit_pro/gross_profit_pro.py:433` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-024 | SQL | `csf_tz/csf_tz/report/gross_profit_pro/gross_profit_pro.py:467` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-025 | SQL | `csf_tz/csf_tz/report/multi_currency_ledger/multi_currency_ledger.py:142` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-026 | SQL | `csf_tz/csf_tz/report/salary_register_ctc/salary_register_ctc.py:124` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-027 | SQL | `csf_tz/csf_tz/report/salary_register_ctc/salary_register_ctc.py:147` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-028 | SQL | `csf_tz/csf_tz/report/salary_register_ctc/salary_register_ctc.py:175` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-029 | SQL | `csf_tz/csf_tz/report/salary_register_ctc/salary_register_ctc.py:227` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-030 | SQL | `csf_tz/csf_tz/report/salary_register_ctc/salary_register_ctc.py:250` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-031 | SQL | `csf_tz/csf_tz/report/salary_register_summary/salary_register_summary.py:81` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-032 | SQL | `csf_tz/csf_tz/report/salary_register_summary/salary_register_summary.py:92` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-033 | SQL | `csf_tz/csf_tz/report/salary_register_summary/salary_register_summary.py:110` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-034 | SQL | `csf_tz/csf_tz/report/salary_register_summary/salary_register_summary.py:128` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-035 | SQL | `csf_tz/csf_tz/report/salary_register_summary_with_components/salary_register_summary_with_components.py:73` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-036 | SQL | `csf_tz/csf_tz/report/salary_register_summary_with_components/salary_register_summary_with_components.py:84` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-037 | SQL | `csf_tz/csf_tz/report/salary_register_summary_with_components/salary_register_summary_with_components.py:102` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-038 | SQL | `csf_tz/csf_tz/report/salary_register_summary_with_components/salary_register_summary_with_components.py:120` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-039 | SQL | `csf_tz/csf_tz/report/stock_balance_pivot_warehouse/stock_balance_pivot_warehouse.py:41` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-040 | SQL | `csf_tz/csf_tz/report/stock_balance_pivot_warehouse/stock_balance_pivot_warehouse.py:64` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-041 | SQL | `csf_tz/csf_tz/report/stock_balance_pivot_warehouse/stock_balance_pivot_warehouse.py:96` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-042 | SQL | `csf_tz/csf_tz/report/stock_balance_pro/stock_balance_pro.py:171` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-043 | SQL | `csf_tz/csftz_hooks/customer.py:13` | Query Builder, bound values, or validated SQL fragments | Re-audit pending |
| SEC-044 | Permissions | `csf_tz/csf_tz/doctype/csf_tz_settings/csf_tz_settings.json:599` | No All role on target branch | Re-audit pending |
| SEC-045 | Permissions | `csf_tz/csf_tz/report/heslb_return_online/heslb_return_online.json:50` | No All role on target branch | Re-audit pending |
| SEC-046 | Permissions | `csf_tz/csf_tz/report/itx.215.03.e_sdl_monthly_returns/itx.215.03.e_sdl_monthly_returns.json:50` | No All role on target branch | Re-audit pending |
| SEC-047 | Permissions | `csf_tz/csf_tz/report/nssf_con5_monthly_contribution___online_version/nssf_con5_monthly_contribution___online_version.json:50` | No All role on target branch | Re-audit pending |
| SEC-048 | Permissions | `csf_tz/csf_tz/report/salary_register_ctc/salary_register_ctc.json:41` | No All role on target branch | Re-audit pending |
| SEC-049 | Permissions | `csf_tz/csf_tz/report/salary_register_summary_with_monthly_comparison/salary_register_summary_with_monthly_comparison.json:41` | No All role on target branch | Re-audit pending |
| SEC-050 | File access | `csf_tz/csftz_hooks/payroll.py:205` | In-memory access or validated filesystem path | Re-audit pending |
| SEC-051 | File access | `csf_tz/csftz_hooks/payroll.py:208` | In-memory access or validated filesystem path | Re-audit pending |
| SEC-052 | File access | `csf_tz/patches/tz_post_code/create_tz_post_code.py:64` | In-memory access or validated filesystem path | Re-audit pending |
| SEC-053 | File access | `csf_tz/stanbic/doctype/stanbic_payments_initiation/stanbic_payments_initiation.py:89` | In-memory access or validated filesystem path | Re-audit pending |
| SEC-054 | File access | `csf_tz/stanbic/xml.py:5` | In-memory access or validated filesystem path | Re-audit pending |
| SEC-055 | File access | `csf_tz/utils/create_custom_fields.py:14` | In-memory access or validated filesystem path | Re-audit pending |
| SEC-056 | File access | `csf_tz/utils/create_property_setter.py:13` | In-memory access or validated filesystem path | Re-audit pending |

## Verification

CI must pass; payroll, stock, finance and bank regression parity should be checked. A scanner rule ceasing to match is not proof of security. Existing role fixes must be validated on migrated sites. Correctness and screenshots are tracked separately.
