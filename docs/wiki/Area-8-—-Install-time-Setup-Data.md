# Area 8 — Install-time Setup Data

## Why it is localisation

Fresh csf_tz installs need a Tanzania-shaped chart of accounts, VAT templates, payroll components, and leave types — none of which exist in vanilla ERPNext. The seed JSON is intentionally **install-only** so that re-running migrate on a populated site does not duplicate records or overwrite user customisations.

## Components

**Source files** under `csf_tz/setup_data/`:

| File | Seeds |
|------|-------|
| `accounts.json` | TZ chart of accounts skeleton |
| `sales_taxes_and_charges_templates.json` | Standard (18%), Zero Rated, Exempt, Special Rate, Special Relief |
| `purchase_taxes_and_charges_templates.json` | Mirror of above for purchases |
| `item_tax_templates.json` | Per-item VAT templates |
| `salary_components.json` | PAYE / NSSF / WCF / SDL / HESLB components |
| `salary_structures.json` | Default TZ structure |
| `leave_types.json` | TZ leave types |
| `leave_policies.json` | TZ leave policy mapping |

**Loader**

- `csf_tz.utils.setup.execute` — called from `after_install` (not `after_migrate`).

## Expected behaviour

| Test | Steps | Expected result |
|------|-------|-----------------|
| Fresh install | New site + `install-app csf_tz` | All seed files load: accounts, tax templates, item-tax templates, salary components, salary structure, leave types, leave policies. Spot-check via the relevant list views. |
| `Standard (18%)` Sales template seeded with the recent fix | Open Sales Taxes and Charges Template = `Standard (18%) - <abbr>` | `is_default = 1`; tax row has `rate = 18` (the recent fix) |
| `Standard (18%)` Purchase template seeded with the recent fix | Open Purchase Taxes and Charges Template = `Standard (18%) - <abbr>` | `is_default = 1`; tax row has `rate = 18` |
| Re-run `bench migrate` on an existing site | `bench --site <site> migrate` | Setup data is **not** re-seeded (no duplicate records / no name clashes). Custom fields and property setters *are* re-applied. |
| Manually re-run setup on a non-empty site | `bench execute csf_tz.utils.setup.execute` | Either: documented to be unsafe (and the user must understand), or: idempotent. Confirm behaviour. |

## Regression notes

- We intentionally do **not** call `setup.execute` from `after_migrate` — calling it on an existing site would create duplicate records under different names. This is by design; do not re-introduce.
- The `Standard (18%)` defaults were added recently. Older sites (installed before the fix) will have the template but without the rate/default; that's expected and intentional (don't auto-update existing user-customisable records).

## See also

- [[Pre-requisites]]
- [[Area 4 — Tax Category and VAT Lookup]]
- [[Area 9 — CSF TZ Settings]]
