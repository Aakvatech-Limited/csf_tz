# Area 2 — Customer TIN / VRN Handling

## Why it is localisation

TIN (Tax Identification Number) and VRN (VAT Registration Number) are TRA taxpayer identifiers with a specific format (9 digits for TIN). csf_tz normalises whatever the user enters so downstream code — especially [[Area 1 — VFD EFD Fiscalisation]] — can rely on a clean value.

## Components

- **Hook:** `Customer.validate` → `csf_tz.customer.clean_and_update_tax_id_info`

## Expected behaviour

| Test | Steps | Expected result |
|------|-------|-----------------|
| Save a Customer with messy TIN | New Customer; Tax ID = `123 456 789` (spaces) → save | Tax ID is stored as `123456789` (normalised) |
| Save a Customer with dashes / mixed format | Tax ID = `12-345-6789` → save | Normalised to `123456789` |
| Save a Customer with an invalid format | Tax ID = `ABCD` (too short, non-numeric) → save | Either validation error (translated) **or** consistent rejection — must not silently accept malformed data |
| Save a Customer with no Tax ID | Empty Tax ID → save | Allowed (some non-VAT customers don't have one), no exception |

## Regression notes

- Earlier versions stored the raw entered string, which then failed at VFD submission with cryptic upstream errors. The cleanup must happen at `Customer.validate`, not later.

## See also

- [[Area 1 — VFD EFD Fiscalisation]]
