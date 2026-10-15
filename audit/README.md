# Frappe Cloud audit finding register

**Original scan summary:** 76 security + 421 correctness = **497 warnings**.

This directory tracks **one immutable record per scanner finding**, not one row per file, PR, or rule. The original raw Semgrep result files were **not available** when this register was created. The count alone cannot establish the 497 identities; do not invent entries or mark them resolved based on PR descriptions.

## Load the baseline
Export the original Frappe Cloud scanner output as Semgrep JSON for each category (or split the combined result into category-specific JSON with its original check IDs and fingerprints). Then run:

```sh
python scripts/audit_findings.py import security.json --kind security
python scripts/audit_findings.py import correctness.json --kind correctness
python scripts/audit_findings.py check
```

Each imported row is **open** by default. Keep original JSON scans in the audit evidence archive if permitted; do not commit sensitive scanner output.

## Resolution rules
Set `status` to `open`, `in_progress`, `needs_review`, `fixed`, `false_positive`, `accepted_risk`, or `superseded`.

Every closed finding requires disposition, reviewer, review date, and a written technical justification in notes. Fixed findings additionally require a PR and test evidence. Link the exact commit and report/line where practical. The status check fails on missing evidence or missing baseline rows.

Run a fresh scan and reconcile with:

```sh
python scripts/audit_findings.py reconcile security-latest.json --kind security
python scripts/audit_findings.py reconcile correctness-latest.json --kind correctness
python scripts/audit_findings.py check
```

**Never delete historic rows.** A warning absent from a later scan becomes `needs_review` unless already dispositioned. A closed warning that reappears becomes `needs_review`; new scanner findings are appended as open, not conflated with the original 497.

## Audit trail of code changes (not automatically equivalent to resolved warnings)
- [PR #504](https://github.com/Aakvatech-Limited/csf_tz/pull/504): initial Query Builder and CI corrections.
- [PR #507](https://github.com/Aakvatech-Limited/csf_tz/pull/507): access controls, Customer GL query, worker ID.
- [PR #508](https://github.com/Aakvatech-Limited/csf_tz/pull/508): warehouse and exchange-differences reports.
- [PR #510](https://github.com/Aakvatech-Limited/csf_tz/pull/510): timesheet, loan and trial balance report queries.

These are candidate remediation evidence. **No finding is considered cleared until individually reconciled and reviewed.**
