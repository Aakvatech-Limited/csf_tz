# Area 7 — Payroll Statutory Overrides

## Why it is localisation

Tanzanian payroll has statutory components (PAYE, NSSF, WCF, SDL, HESLB, etc.) and an approval workflow specific to Tanzania. csf_tz implements these through doctype class overrides and validation hooks.

## Components

**Class overrides**

| Doctype | csf_tz override |
|---------|-----------------|
| `Salary Slip` | `csf_tz.hrms_overrides.salary_slip.CustomSalarySlip` |
| `Additional Salary` | `csf_tz.hrms_overrides.additional_salary.CustomAdditionalSalary` |
| `Leave Encashment` | `csf_tz.hrms_overrides.leave_encashment.CustomLeaveEncashment` |

(Exact paths may vary by branch — verify via `override_doctype_class` in `hooks.py`.)

**Hooks**

- `Payroll Entry.before_insert` → `before_insert_payroll_entry`
- `Salary Slip.on_submit` → payroll-approval flow advance
- `Additional Salary.on_submit` → `create_additional_salary_journal`
- `Leave Encashment.validate` → `validate_flags`

**Custom fields**

- Payroll-approval custom fields on `Payroll Entry` and `Salary Slip`
- Payroll cost-center custom field (back-filled by patch `update_salary_slips_from_currrent_employee_payroll_cost_center`)

## Expected behaviour

| Test | Steps | Expected result |
|------|-------|-----------------|
| Create a Payroll Entry | New PE for a TZ employee → save | `before_insert_payroll_entry` runs; payroll-approval custom fields visible on the form |
| Submit a Salary Slip | Generate slip from PE → submit | Overridden `SalarySlip` computes statutory components (PAYE / NSSF / WCF / SDL bands) per the TZ formulas |
| Submit an Additional Salary | Create + submit an Additional Salary | `create_additional_salary_journal` posts a corresponding Journal Entry |
| Approval flow advance | Submit slip as a payroll user → as approver, click approve | Approval status advances; only approvers in the configured Role can transition |
| Leave Encashment validation | Submit a Leave Encashment with bad flag combination (e.g. encash + carry-forward) | `validate_flags` blocks with the translated rule message |
| Re-run salary slip for an updated employee | Update employee's payroll cost centre → re-generate slip | Slip uses the *current* cost centre (patch back-fills historical slips on migrate) |

## Regression notes

- The cost-centre back-fill patch is one-shot. If you re-run on an already-patched site, it must be idempotent (no duplicate updates). Confirm by running `bench migrate` twice.
- The TZ statutory bands are version-sensitive — check the slip's component breakdown against the current TRA / NSSF / WCF rate schedule.
