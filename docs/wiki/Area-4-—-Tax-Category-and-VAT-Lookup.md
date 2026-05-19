# Area 4 — Tax Category and VAT Lookup

## Why it is localisation

Tanzanian VAT is 18% standard rate, with zero-rated, exempt, and special-relief categories. csf_tz resolves the correct `Tax Category` for a given customer + company combination so the right Sales Taxes and Charges template is applied.

## Components

- `csf_tz.custom_api.get_tax_category(doc_type, company)` — whitelisted; called from `sales_invoice.js` and `delivery_note.js` `customer` triggers.
- `csf_tz.custom_api.validate_grand_total` — called from `Sales Invoice.validate` (via feature flag in CSF TZ Settings).

## Expected behaviour

| Test | Steps | Expected result |
|------|-------|-----------------|
| Create a Sales Invoice for a customer with **no** tax category set | New SI, pick a customer that has Tax Category = blank | `get_tax_category` returns `""` (empty string); SI saves; **no** `LinkValidationError` for Tax Category |
| Create a Sales Invoice for a customer **with** a tax category | Customer has Tax Category = `Standard (18%)` | SI auto-applies the right `taxes_and_charges` template; tax row(s) appear |
| Submit an SI with a negative grand total | Manually adjust items so the total goes negative → submit | Blocked with a translated message (unless this is an intentional offset / credit scenario configured in settings) |
| Switch customer mid-edit | Change the customer on a draft SI | Tax Category re-resolves; old taxes are not retained |
| Tanzania Tax — both Purchase + Sales | New Purchase + Sales templates from `setup_data/` exist | "Standard (18%)" purchase + sales templates are seeded with `is_default = 1` and `rate = 18` (after the recent setup_data fix) |

## Regression notes

- **The `[""]` regression:** an earlier bug returned a single-element list `[""]` from `get_tax_category` instead of `""`, causing `Could not find Tax Category: ['']` on every customer change. The fix ensures `""` (empty string). Please re-confirm this stays fixed.
- The default "Standard (18%)" template recently gained `"is_default": 1` and `"rate": 18` in setup_data JSON — confirm the fresh-install seeded templates carry both.

## See also

- [[Area 1 — VFD EFD Fiscalisation]] — VFD requires tax_category to resolve before fiscalising.
- [[Area 8 — Install-time Setup Data]] — seeded VAT templates.
