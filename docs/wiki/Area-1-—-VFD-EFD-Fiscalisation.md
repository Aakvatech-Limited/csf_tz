# Area 1 — VFD / EFD Fiscalisation

> **Priority: highest.** This is *the* core compliance area. A VFD (Virtual Fiscal Device) issues TRA-registered fiscal receipts for every Sales Invoice. Failure here is a statutory failure.

---

## Why it is localisation

The Tanzania Revenue Authority (TRA) mandates that every taxable Sales Invoice be fiscalised through an approved VFD provider, producing a receipt number and (in newer formats) a QR code. csf_tz wraps the provider APIs so ERPNext invoices auto-fiscalise on submit.

## Components

**Doctypes** (provider-side)

- `Simplify VFD Settings`
- `VFDPlus Settings`
- `Total VFD Setting`
- `VFD Provider` (selector)

**Doctypes** (fiscal-record side)

- `EFD Z Report`, `EFD Z Report Invoice`
- `TRA Tax Inv`, `TRA Tax Inv Item`

**Hooks** (from `hooks.py`)

| Event | Hook | When |
|-------|------|------|
| `Sales Invoice.before_submit` | `vfd_validation` | Blocks non-compliant invoices |
| `Sales Invoice.on_submit` | `autogenerate_vfd` | Issues fiscal receipt |
| `Sales Invoice.before_cancel` | `validate_cancel` | Enforces TRA cancellation rules |

**Scheduled jobs**

| Frequency | Job |
|-----------|-----|
| every 15 min | `posting_all_vfd_invoices` |
| every 10 min | `get_access_token` |
| every 12 hours | `get_refresh_token` |

---

## Expected behaviour

| Test | Steps | Expected result |
|------|-------|-----------------|
| Configure a VFD provider | Open `Simplify VFD Settings` (or VFDPlus / Total VFD), set Company + credentials, save | Settings save without error; provider record is linked to the Company |
| Submit a fully-valid Sales Invoice with VFD enabled | Create SI for a Tanzania company → submit | `vfd_validation` passes; `autogenerate_vfd` runs; a `TRA Tax Inv` is created; the SI shows a fiscal receipt number / QR |
| Submit an invoice missing required VFD data | Create SI without customer TIN, without item tax, or for an item with no `item_tax_template` → submit | `before_submit` blocks with a clear translated error message; no fiscal record created |
| Cancel a fiscalised SI | Submit + fiscalise → cancel | `validate_cancel` runs; TRA cancellation rules enforced (no silent cancellation of a posted fiscal receipt) |
| Run `posting_all_vfd_invoices` with a pending invoice | Submit an SI; force-fail the live post; wait for the 15-min job (or run manually via `bench execute`) | Pending VFD invoice is re-posted; status updates to `Success` |
| Generate an EFD Z Report | New `EFD Z Report` for a date range | Report lists all fiscalised invoices in the period |
| Token refresh jobs | Trigger `get_access_token` / `get_refresh_token` manually | Tokens refresh without manual intervention; expiry timestamps update |

---

## Manual invocation

If the scheduler is paused, the periodic jobs can be triggered manually:

```bash
# Force the periodic post job
bench --site csf-tz.localhost execute csf_tz.vfd_providers.scheduled.posting_all_vfd_invoices

# Force a token refresh
bench --site csf-tz.localhost execute csf_tz.vfd_providers.scheduled.get_access_token
```

---

## Regression notes

- The `validate_cancel` hook was added because earlier versions allowed silent cancellation of fiscalised invoices — a TRA violation. Please re-confirm cancellation is now blocked or properly recorded.
- `autogenerate_vfd` must not raise on transient provider downtime; failures are queued for `posting_all_vfd_invoices` to retry. Verify by submitting with provider unreachable.

---

## See also

- [[Area 2 — Customer TIN VRN Handling]] — VFD requires a clean customer TIN.
- [[Area 4 — Tax Category and VAT Lookup]] — VAT/tax-category must resolve before fiscalisation.
