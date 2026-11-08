# Tanzania income tax: Phase 1

Phase 1 classifies accounting entries and records the evidence and review decision. It does not calculate annual tax, apply statutory donation limits, determine tax depreciation, file returns or post tax journals. Category names describe a proposed treatment, not legal certification of deductibility.

## Extension model

No Custom Fields, Property Setters, Accounting Dimensions or schema changes are added to Account, GL Entry, Purchase Invoice, Sales Invoice or their child tables.

| Record | Purpose |
| --- | --- |
| TZ Tax Source Mapping | One configuration per source DocType; identifies its existing company and posting-date fields. |
| TZ Tax Account Mapping | Company/ledger defaults, with inclusive effective dates and overlap prevention. |
| TZ Tax Category | Site-maintained classification, proposed treatment and evidence requirement. |
| TZ Tax Transaction Review | Separate extension linked to one GL Entry, its source voucher and original source-row ID. |
| TZ Tax Allocation | Signed company-currency splits; must total exactly the linked posting. |
| TZ Tax Evidence | Attached documents, type, reference, validity and notes. |

One source transaction can have several GL reviews. A GL posting can be split across categories. Use debit-minus-credit signs, including for income and returns. This avoids assigning an invoice's gross total or VAT to its expense classification. Balance-sheet entries are optional in the register and can be reviewed separately.

The source mapping supports other submittable voucher DocTypes with Company and Date fields. It does not invent a universal invoice-item-to-GL relationship: ERPNext can merge ledger postings. The immutable GL reference is authoritative; `source_detail` is displayed when ERPNext supplies it. If entries are merged, split the resulting GL amount and document the source-row reasoning in allocation notes.

## Start using it

1. Migrate the feature branch on an ERPNext v16 test site and rebuild assets.
2. Open **CSF TZ → Income Tax → TZ Tax Review Register**. Income Tax is a separate module in the CSF TZ app, with its own dock entry, sidebar and workspace.
3. As Accounts Manager or System Manager, click **Set Up Tax Categories and Sources**. This explicitly seeds categories and mappings for Purchase Invoice, Sales Invoice, Journal Entry and Payment Entry without overwriting existing records. No account is automatically deemed deductible.
4. Configure company-specific **TZ Tax Account Mapping** records. A mapping applies only to its exact ledger account, not its children.
5. Open a submitted transaction's **Tax → Income Tax Review** button and select a GL entry. Alternatively use the report's GL-entry selector. Add or split classifications, record the reason and attach evidence.
6. Accounts Users prepare drafts. Accounts Managers or System Managers submit/approve them. Cancellation and replacement preserve the prior record; draft and approved active reviews cannot be duplicated for one GL entry.
7. Review exceptions before proceeding to the future annual computation.

The transaction buttons are provided for the four default vouchers and GL Entry. Additional source types work through the register without changing their schema. The existing app navigation is preserved, with a separate Income Tax module entry added to the dock.

## Evidence and review status

Approval requires all allocation categories to be resolved. For an evidence-required category, at least one existing File attachment valid at the posting date is required, or the approving manager must record an explicit exception. Phase 1 checks document presence and date, not legal sufficiency or the content/authenticity of a ruling. Reviewers must assess these. A manager's exception does not establish tax deductibility and remains visible as **Reviewed with Exception**.

| Status | Meaning |
| --- | --- |
| Unreviewed | No saved extension; an account default is only a suggestion. |
| Draft Review | Classification exists but is not approved. |
| Reviewed | Submitted, source fingerprint agrees, required evidence is present. |
| Reviewed with Exception | Submitted with an explicit evidence exception; remains in exceptions. |
| Evidence Required | Required evidence is unavailable or invalid at the posting date. |
| Source Changed | Voucher modification, ledger values or submission status changed after review. |
| Source Mapping Required | Voucher type is not enabled for review. |
| Source Cancelled / GL Entry Replaced | Historical review survives cancellation/reposting; do not include it in current-ledger totals. |

Submitted reviews are snapshots. Correct them by cancellation and replacement, not by changing submitted vouchers. Source fingerprints conservatively include voucher modification time, so even a non-financial source edit prompts review. Existing transactions need no reposting to be classified.

The register has no automatic grand total: it includes different tax treatments, draft allocations and historical exceptions. Source permissions and company restrictions apply; tax review access does not grant access to otherwise restricted vouchers. The existing Accounts User, Accounts Manager and System Manager roles are used.

## Validation

Standalone checks:

```sh
python -m unittest discover -s tests/unit -v
```

Site acceptance checks (must run on a migrated development/test site):

```sh
bench --site <test-site> migrate
bench build --app csf_tz
bench --site <test-site> run-tests --app csf_tz --module csf_tz.income_tax.tests.test_tax_computation_phase_one
```

Also verify Accounts User versus manager approval, company User Permissions, restricted source vouchers, invoice returns, private evidence uploads, simultaneous duplicate creation, cancellation/reposting, missing attachments and the Income Tax workspace/sidebar/dock entry. The standalone suite cannot establish database migration, permissions integration or browser behavior.

## Navigation coverage

The Income Tax workspace and sidebar expose the Review Register, Transaction Review, Account Mapping, Category and Source Mapping. Allocation and Evidence are child tables and deliberately have no standalone menu entries. No new charts, dashboards or number cards are introduced.

## Module layout

All six tax DocTypes, the review register, domain services, permissions, setup and site integration tests live under `csf_tz/income_tax`. Their Frappe module is **Income Tax**, registered in `modules.txt`. Shared transaction buttons remain in the app public assets, with hooks and API calls pointing to the new module. The default CSF TZ module no longer owns tax records or tax navigation. Existing DocType and report names are preserved; run migration and rebuild assets to sync module ownership and client calls.
