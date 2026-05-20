# Area 5 — TZ Geographic Master Data

## Why it is localisation

Tanzania has an administrative hierarchy of Region → District → Ward → Village that does not exist in vanilla ERPNext. Customers, Addresses, and HR records reference this hierarchy for tax/reporting purposes.

## Components

**Doctypes**

- `TZ Region`
- `TZ District` (linked to Region)
- `TZ Ward` (linked to District)
- `TZ Village` (linked to Ward)

**Seeding**

- Initial data via `csf_tz.utils.setup` on fresh install, plus per-tenant import paths if applicable.

## Expected behaviour

| Test | Steps | Expected result |
|------|-------|-----------------|
| Open `TZ Region` list | Navigate to `/app/tz-region` | Tanzanian regions are present (seeded or importable) — Arusha, Dar es Salaam, Dodoma, etc. |
| Open `TZ District` list | Navigate to `/app/tz-district` | Districts present, each links to a Region |
| Open `TZ Ward`, `TZ Village` lists | Navigate to those doctypes | Hierarchy intact; no broken Link fields |
| Use the hierarchy on a Customer / Address | Edit a Customer, set TZ Region → check District filter | Selecting a Region filters the District field to only that Region's districts. Same cascade for Ward and Village. |
| Save with a TZ village set | Set Village = `<some village>` on Customer → save | Saves cleanly; the Region/District/Ward auto-populate from the Village's parents (or are required to match) |

## Regression notes

- The Region → District → Ward → Village cascade uses link filters; verify these still apply (a regression would let you save a Ward under the wrong District).
