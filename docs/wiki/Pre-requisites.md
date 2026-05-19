# Pre-requisites

This page describes the dependency stack and install order required before the localisation areas can be tested.

---

## Required apps

| App | Version | Required? |
|-----|---------|-----------|
| `frappe` | `version-15` | Yes |
| `erpnext` | `version-15` | Yes |
| `csf_tz` | `version-15` *or* `version-15-hotfix` | The app under test |

csf_tz declares no `required_apps` in `hooks.py`, but `erpnext` (on top of `frappe`) is what its doctypes, hooks, and patches target.

> **Optional:** Areas 6 and 7 cover banking and payroll workflows. If you intend to test those Areas, you can additionally install `hrms` and/or `payments`. They are not required to install or use csf_tz itself — only to exercise those specific Area pages.

---

## Install

```bash
# 1. Bench + Frappe
bench init --frappe-branch version-15 csf-tz-bench
cd csf-tz-bench

# 2. Get apps
bench get-app --branch version-15 erpnext
bench get-app --branch version-15-hotfix https://github.com/Aakvatech-Limited/csf_tz.git

# 3. Create site (TZS as default currency is recommended)
bench new-site csf-tz.localhost \
    --db-root-password root \
    --admin-password admin

# 4. Install in this order
bench --site csf-tz.localhost install-app erpnext
bench --site csf-tz.localhost install-app csf_tz
```

---

## Post-install verification

After installation, confirm the install hooks ran. The expected `after_install` chain from [hooks.py](https://github.com/Aakvatech-Limited/csf_tz/blob/version-15-hotfix/csf_tz/hooks.py) is:

```
csf_tz.utils.create_custom_fields.execute     → adds TZ custom fields
csf_tz.utils.create_property_setter.execute   → adjusts ERPNext property defaults
csf_tz.utils.setup.execute                    → seeds setup_data/*.json (fresh-install only)
```

Spot-checks:

```bash
bench --site csf-tz.localhost console
```

```python
import frappe

# 1) CSF TZ Settings single doctype exists
frappe.get_single("CSF TZ Settings")

# 2) Custom field on Sales Invoice was added (TZ-specific tax fields)
frappe.db.exists("Custom Field", {"dt": "Sales Invoice", "fieldname": "tz_vfd_provider"})

# 3) TZ master data seeded
frappe.db.count("TZ Region")  # > 0 if seeded

# 4) Tanzania tax templates seeded
frappe.db.exists("Sales Taxes and Charges Template", "Standard (18%) - <abbr>")
```

If any of the above return `None` / `0` / `False`, the install hooks did not run — re-run `bench --site csf-tz.localhost install-app csf_tz` after confirming the dependency order above.

---

## Recommended test company

| Field | Value |
|-------|-------|
| Country | Tanzania |
| Default currency | TZS |
| Chart of accounts | TZ (loaded by `setup_data/accounts.json`) |
| Tax templates | Standard (18%) — Sales & Purchase |

A real TIN/VRN is **not** required (test fixtures will work); the format validation is what matters.

---

## Optional: seed sample data

For convenience, the `setup_data/` folder contains TZ-localised seed JSON. To re-run it on an existing site (without re-installing the app):

```bash
bench --site csf-tz.localhost execute csf_tz.utils.setup.execute
```

> ⚠️ `setup.execute` is normally only called on **fresh install**. Calling it on a populated site may insert duplicates if the seed records already exist under different names. Use only on a clean site.
