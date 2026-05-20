# Area 9 — CSF TZ Settings

## Why it is localisation

`CSF TZ Settings` is a Single doctype that acts as the master switch for every localisation behaviour above. Each toggle gates a specific hook so that operators can disable a feature on a per-site basis without uninstalling the app.

## Components

**Single doctype:** `CSF TZ Settings`

**Tabs** (organised post-refactor):

1. **Sales & Purchase** — VFD, WHT, VAT-lookup, tax-category, auto-create Delivery Note
2. **Stock & Accounting** — Stock-entry / GL / inter-company controls
3. **HR & Payroll** — Payroll approval flow, additional-salary journal, leave encashment rules
4. **System & Data** — TZ master-data toggles, scheduled-job toggles, integration credentials

(Exact field list lives in [csf_tz_settings.json](https://github.com/Aakvatech-Limited/csf_tz/blob/version-15-hotfix/csf_tz/csf_tz/doctype/csf_tz_settings/csf_tz_settings.json).)

## Expected behaviour

| Test | Steps | Expected result |
|------|-------|-----------------|
| Open `CSF TZ Settings` | Navigate to `/app/csf-tz-settings` | Loads with all four tabs; no orphan / blank sections; no JS console errors |
| Save the doctype | Open → save (no changes) | Saves cleanly; `validate` doesn't raise |
| Toggle a feature flag — e.g. WHT off | Disable WHT toggle → save → submit a WHT-flagged SI | The corresponding hook respects the flag (no WHT GL entries posted) — see [[Area 3 — Withholding Tax GL Entries]] |
| Toggle a feature flag — e.g. auto-create Delivery Note off | Disable the flag → submit an SI for a stock item | No DN auto-created |
| Single-value reads | Backend: `frappe.db.get_single_value("CSF TZ Settings", "<flag>")` | Returns the stored value cleanly (not `None` for set flags) |
| Re-open in incognito | Different user with System Manager role | Settings same; permissions consistent |

## Regression notes

- Settings was refactored into 4 tabs in `version-15-hotfix`. If the form shows the old flat layout, the build is stale — clear cache and refresh.
- Some flags previously read via `frappe.db.get_value` were migrated to `frappe.db.get_single_value` (the correct API for Single doctypes). Verify the change took: a `get_value` against a Single doctype returns `None` and will silently disable the gated feature.

## See also

- All other Areas — each is gated by at least one flag here.
