# Area 3 — Withholding Tax GL Entries

## Why it is localisation

Tanzanian WHT (Withholding Tax) is a statutory deduction that must post to dedicated GL accounts on submit and reverse on cancel. csf_tz adds the GL postings on top of the ERPNext SI/PI workflow.

## Components

| Hook | Function |
|------|----------|
| `Sales Invoice.on_submit` | `csf_tz.custom_api.make_withholding_tax_gl_entries_for_sales` |
| `Purchase Invoice.on_submit` | `csf_tz.custom_api.make_withholding_tax_gl_entries_for_purchase` |

Both are guarded by feature flags on **CSF TZ Settings** (see [[Area 9 — CSF TZ Settings]]).

## Setup needed before testing

1. Enable the WHT flag in `CSF TZ Settings`.
2. Configure a **Withholding Tax account** on the Company (`default_withholding_tax_account` custom field).
3. The customer/supplier or the Item must be flagged for WHT (per your seed data).

## Expected behaviour

| Test | Steps | Expected result |
|------|-------|-----------------|
| Submit a WHT-applicable Sales Invoice | SI with a WHT-flagged customer, submit | Standard GL entries **plus** additional GL entries posting the WHT amount to the WHT account |
| Submit a WHT-applicable Purchase Invoice | PI with a WHT-flagged supplier, submit | WHT GL entries posted on the purchase side, with the supplier as the contra |
| Cancel either of the above | Cancel the submitted doc | WHT GL entries are reversed; balance returns to pre-submit state |
| Submit an invoice with the WHT flag disabled in settings | Disable in CSF TZ Settings → submit a WHT-flagged invoice | **No** extra GL entries are posted (flag respected) |
| Re-submit after fix | Fix WHT setup error → re-submit | GL entries post cleanly; no duplicate entries from a prior failed attempt |

## Regression notes

- Cancellation must reverse the WHT entries — confirm via the GL Entry report filtered by the SI/PI.
- The WHT account must be in the same Company as the invoice; cross-company WHT postings indicate a misconfiguration.
