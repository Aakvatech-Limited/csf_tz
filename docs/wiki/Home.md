# CSF TZ — Localisation Wiki

[`csf_tz`](https://github.com/Aakvatech-Limited/csf_tz) is the Tanzania localisation app for the [Frappe](https://frappeframework.com/) / [ERPNext](https://erpnext.com/) stack. It implements the statutory, compliance, and regional functionality required to run ERPNext for a Tanzanian entity, including:

- VFD / EFD fiscalisation against the Tanzania Revenue Authority (TRA)
- Tanzanian VAT handling and tax-category resolution
- Withholding tax GL postings on sales and purchase invoices
- Tanzanian payroll statutory components and approval workflow
- NMB / KCB / Stanbic banking integrations
- Region → District → Ward → Village master data

This wiki documents each area: the components involved, the expected behaviour, and notes on previously fixed regressions.

---

## How to use this wiki

1. Set up a site by following [[Pre-requisites]].
2. Walk through Areas 1–9 in the sidebar. Each Area page lists:
   - **Components** — the doctypes and hooks involved.
   - **Expected behaviour** — concrete actions and the result they produce.
   - **Regression notes** — behaviours that have been hardened against earlier bugs.
3. Each Area is independent and can be read in any order.

---

## Required apps

To install and use csf_tz, you need:

| App | Version |
|-----|---------|
| `frappe` | `version-15` |
| `erpnext` | `version-15` |

A v16 hotfix branch (`version-16-hotfix`) tracks the same areas against `version-16` of frappe and erpnext.

---

## Localisation areas

| # | Area | What it covers |
|---|------|----------------|
| 1 | [[Area 1 — VFD EFD Fiscalisation]] | TRA-mandated fiscal receipts on every Sales Invoice |
| 2 | [[Area 2 — Customer TIN VRN Handling]] | TRA taxpayer identification format on Customers |
| 3 | [[Area 3 — Withholding Tax GL Entries]] | Statutory WHT GL entries on Sales/Purchase Invoice |
| 4 | [[Area 4 — Tax Category and VAT Lookup]] | TZ VAT category resolution on Sales Invoice |
| 5 | [[Area 5 — TZ Geographic Master Data]] | Region → District → Ward → Village master data |
| 6 | [[Area 6 — Localised Banking]] | NMB / KCB / Stanbic integrations + bank charges |
| 7 | [[Area 7 — Payroll Statutory Overrides]] | TZ payroll components, approval flow, leave rules |
| 8 | [[Area 8 — Install-time Setup Data]] | TZ chart of accounts, tax templates, salary components |
| 9 | [[Area 9 — CSF TZ Settings]] | Single control panel that toggles every area above |

---

## Issues

To report a bug or behavioural divergence, open an issue at <https://github.com/Aakvatech-Limited/csf_tz/issues> with the Area number in the title.

---

## Contact

For questions, contact **info@aakvatech.com**.
