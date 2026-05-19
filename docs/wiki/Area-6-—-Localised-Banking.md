# Area 6 — Localised Banking (NMB / KCB / Stanbic)

## Why it is localisation

Tanzanian banks expose proprietary integration formats (SFTP file drops, bank-statement layouts) that ERPNext does not handle natively. csf_tz adds:

- Bank charge auto-posting via configurable patterns
- Stanbic / KCB SFTP statement sync
- Bank-format payroll file exports

## Components

**Modules / files**

- `csf_tz/kcb/` (KCB-specific)
- `csf_tz/stanbic/` (Stanbic SFTP)
- `csf_tz/bank_api.py` (reconciliation entry point)

**Doctypes**

- `CSF TZ Bank Charges`
- `Bank Charges Pattern`
- `Bank Clearance Pro`

**Hooks / scheduled jobs**

| Trigger | What |
|---------|------|
| `Payment Entry.validate` | `validate_bank_charges_account` |
| `Payment Entry.on_submit` | `create_bank_charges_journal` |
| Daily | `csf_tz.bank_api.reconciliation` |
| Stanbic SFTP polling | `sync_all_stanbank_files`, `process_download_files` |

## Expected behaviour

| Test | Steps | Expected result |
|------|-------|-----------------|
| Configure a `Bank Charges Pattern` | New `Bank Charges Pattern`, set match criteria (account, description regex), save | Pattern saves; appears in the auto-match list |
| Submit a Payment Entry that matches a pattern | Submit a PE whose description matches the pattern | `validate_bank_charges_account` passes; `create_bank_charges_journal` auto-creates a Journal Entry for the bank charge portion |
| Submit a PE with no matching pattern | Submit a PE that doesn't match any pattern | No bank-charge journal posted — silent pass |
| Daily reconciliation job | `bench --site <site> execute csf_tz.bank_api.reconciliation` | Runs without error; reconciles configured bank statements |
| Stanbic SFTP sync | Configure Stanbic credentials; run `sync_all_stanbank_files` | Statements pulled from SFTP into `Bank Transaction` records |
| Stanbic SFTP not configured | Run the same job on a site with no SFTP creds | Skips cleanly with a clear log message — no traceback |
| KCB / Stanbic payroll export | From Payroll Entry → export bank file | File generated in the bank-specific format (CSV with the required column layout) |

## Regression notes

- The Stanbic SFTP jobs must **skip cleanly** when credentials aren't set (don't raise). This is important because the same code runs on sites that don't use Stanbic.
- `create_bank_charges_journal` is wrapped in a feature flag in `CSF TZ Settings` — make sure disabling the flag turns off the auto-journal.

## See also

- [[Area 9 — CSF TZ Settings]] — Bank-charges feature flag.
