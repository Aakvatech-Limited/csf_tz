# CSF TZ Spec

CSF TZ provides country-specific functionality for Tanzania on top of Frappe and ERPNext.

The application extends standard ERPNext behaviour rather than replacing ERPNext. Tanzanian statutory requirements, integrations, local business rules, accounting extensions, payroll extensions, banking functionality, and other reusable Tanzania-specific functionality belong in CSF TZ when they cannot reasonably be implemented through standard ERPNext configuration.

The application should preserve ERPNext conventions and upgradeability wherever possible.

## Goals

* Provide reusable Tanzania-specific functionality for ERPNext.
* Support Tanzanian statutory, taxation, fiscal, payroll, banking, regulatory, and business requirements.
* Extend standard ERPNext transactions without unnecessarily duplicating ERPNext functionality.
* Keep integrations with Tanzanian authorities, fiscal systems, banks, and payment providers isolated behind clear interfaces.
* Keep custom business logic deterministic, auditable, and maintainable.
* Make upgrades between supported Frappe and ERPNext versions predictable.
* Keep site-specific or customer-specific functionality outside the common CSF TZ application unless it is genuinely reusable.
* Prefer standard Frappe extension mechanisms over modifications to Frappe or ERPNext source code.

## Application Model

CSF TZ is an extension application running inside a Frappe/ERPNext site.

The important architectural areas are:

* **DocTypes** own persistent CSF TZ business entities and configuration.
* **Hooks** connect CSF TZ behaviour to Frappe and ERPNext lifecycle events.
* **Overrides** replace standard document controller behaviour only when extension through hooks is insufficient.
* **Client scripts and bundled JavaScript** extend standard Desk behaviour.
* **APIs** expose explicitly supported server-side operations and integrations.
* **Integrations** communicate with banks, payment providers, fiscal systems, government authorities, and other external services.
* **Scheduled jobs** perform recurring reconciliation, synchronization, notification, regulatory, and maintenance work.
* **Patches** perform controlled schema, metadata, configuration, and data migrations.
* **Reports** expose business, accounting, operational, and statutory information.
* **Workspaces** provide user-facing entry points into Tanzania-specific functionality.

Business rules should live as close as possible to the domain that owns them.

Do not place substantial business logic in `hooks.py`. Hooks should primarily map framework events to appropriately grouped implementation functions.

## Functional Domains

The application may contain functionality covering areas including:

* Tanzania tax and fiscal compliance
* VFD/EFD integrations
* Sales and receivables extensions
* Purchasing and payables extensions
* Withholding taxes
* Banking and reconciliation
* Payroll and employee-related localization
* Inventory and stock controls
* Importation and landed-cost processes
* Payment provider integrations
* Tanzanian geographic and regulatory data
* Vehicle and authority integrations
* Education-related extensions where required by supported deployments
* Operational utilities and reusable ERPNext enhancements

A feature does not belong in CSF TZ merely because it was developed for a Tanzanian customer.

New functionality should normally satisfy at least one of these conditions:

1. It implements a Tanzanian statutory or regulatory requirement.
2. It integrates with a Tanzania-specific service or institution.
3. It represents a business requirement broadly reusable by CSF TZ installations.
4. It provides infrastructure required by another legitimate CSF TZ feature.

Customer-specific workflows, reports, integrations, fields, naming conventions, or business rules should normally live in a customer-specific application.

## Extension Model

Use Frappe's standard extension mechanisms in this order of preference:

1. Configuration and standard ERPNext functionality
2. Custom fields and property setters managed by the application
3. Document events
4. Client-side DocType extensions
5. Whitelisted methods and APIs
6. Scheduler events
7. Controller extension or override where required

Direct modification of Frappe or ERPNext source code is not part of the CSF TZ architecture.

### Document Events

Use `doc_events` when logic belongs to a standard Frappe or ERPNext document lifecycle.

Event handlers should:

* receive the document and event using standard Frappe conventions;
* perform one clearly identifiable business responsibility;
* avoid duplicating ERPNext controller logic;
* avoid committing or rolling back database transactions independently unless specifically required;
* raise meaningful validation errors when a transaction cannot proceed;
* remain safe when called during normal framework lifecycle processing.

Large handlers should delegate to domain-specific modules.

### Controller Overrides

Controller overrides are a high-impact extension mechanism.

Use `override_doctype_class` only when the required behaviour cannot safely be implemented through events or supported extension points.

An override should inherit from the corresponding upstream controller wherever practical.

When overriding a standard controller:

* preserve upstream behaviour unless the specification explicitly changes it;
* call the superclass implementation where appropriate;
* document why an override is required;
* consider upstream changes during every major ERPNext upgrade;
* keep the override narrowly scoped.

Controller overrides should not become independent copies of ERPNext controllers.

## Client-Side Extensions

JavaScript attached through `doctype_js`, `doctype_list_js`, application bundles, or other Frappe hooks should enhance the standard UI rather than reproduce server-side business logic.

Client-side code may:

* improve data entry;
* provide validations for user convenience;
* calculate previews;
* add buttons and actions;
* call approved server methods;
* adapt standard forms to CSF TZ workflows.

Business-critical validation must also exist server-side.

Never rely only on browser-side validation for accounting, compliance, authorization, statutory, or data-integrity controls.

## API Model

Server APIs should be grouped by domain rather than accumulating unrelated behaviour in large generic modules.

New APIs should preferably live in a dedicated package or domain module.

Whitelisted methods must explicitly consider:

* authentication;
* authorization;
* input validation;
* document permissions;
* idempotency;
* transaction boundaries;
* external-service failures;
* logging;
* exposure of confidential data.

Do not make a method guest-accessible unless anonymous access is a genuine integration requirement.

Public or integration-facing APIs should have stable request and response contracts.

Breaking API changes should be treated as compatibility changes.

## Integration Model

External systems should be treated as unreliable network dependencies.

Integrations may include:

* VFD/EFD providers;
* TRA-related services;
* banks;
* payment gateways;
* SFTP endpoints;
* vehicle and licensing authorities;
* regulatory services;
* other approved third-party systems.

Integration code should separate:

1. configuration;
2. authentication;
3. request construction;
4. transport;
5. response parsing;
6. business processing;
7. retry/reconciliation behaviour;
8. logging.

Provider-specific behaviour should remain inside provider-specific modules wherever possible.

Do not spread provider-specific conditionals throughout Sales Invoice, Payment Entry, Payroll Entry, or other unrelated domains.

### Credentials

Credentials, tokens, private keys, API secrets, passwords, and similar material must never be hard-coded in source files.

Use Frappe configuration or password fields appropriate to the sensitivity of the credential.

Logs must not expose credentials or sensitive authentication material.

### External Calls

External calls performed during document submission should be used carefully.

Where an external operation can safely occur asynchronously, prefer a background or reconciliation process rather than making the external provider's availability a prerequisite for completing an ERPNext transaction.

Where synchronous communication is legally or operationally required, failure behaviour must be explicit.

## VFD and Fiscal Processing

Fiscal processing is compliance-sensitive functionality.

VFD functionality should maintain a clear distinction between:

* ERPNext transaction state;
* fiscal submission state;
* provider request state;
* provider response state;
* retries;
* successful fiscalization;
* failure;
* cancellation or reversal.

A Sales Invoice being submitted in ERPNext does not by itself prove successful fiscal submission.

Fiscal operations should preserve enough information to determine:

* what was submitted;
* when it was submitted;
* which provider was used;
* what response was received;
* whether the operation succeeded;
* whether retry is required;
* whether subsequent cancellation or adjustment occurred.

Provider communication and fiscal business rules should be kept separate wherever practical.

## Accounting Integrity

Any CSF TZ functionality that creates or alters accounting consequences must respect ERPNext's accounting model.

Examples include:

* withholding tax;
* bank charges;
* exchange differences;
* landed costs;
* import tracking;
* additional salary accounting;
* payment integrations.

Accounting logic must:

* use submitted documents where ERPNext requires submission;
* preserve company and currency context;
* preserve debit/credit integrity;
* respect cancellation;
* avoid orphan accounting references;
* avoid duplicate GL consequences;
* remain reproducible from the underlying business transaction.

Do not update accounting tables directly when an ERPNext document or accounting API should own the transaction.

## Scheduled Jobs

Recurring processing is registered through Frappe scheduler hooks.

Scheduled jobs are appropriate for work including:

* synchronization;
* reconciliation;
* retries;
* token renewal;
* regulatory data refreshes;
* notifications;
* queue seeding;
* periodic cleanup;
* maintenance;
* delayed transaction processing.

Scheduler methods must be safe to execute repeatedly.

Where possible they should be idempotent: running the same job again should not create duplicate financial, regulatory, or operational consequences.

A scheduled job should not assume that the previous invocation completed successfully.

Jobs processing potentially large datasets should operate in bounded batches.

Do not load an unbounded number of documents into memory.

Failures affecting one record should not unnecessarily prevent all other independent records from processing.

## Background Work

Operations involving significant network communication, file processing, large datasets, or long-running calculations should normally use Frappe background jobs.

Queue work when synchronous execution would:

* make a user transaction unnecessarily slow;
* risk HTTP timeouts;
* depend on unreliable third-party services;
* process large numbers of records;
* perform retryable work.

Background jobs must receive enough identifiers to reload authoritative state rather than depending on stale in-memory documents.

## Configuration

CSF TZ configuration should use Frappe DocTypes or supported site configuration.

Configuration belongs at the narrowest appropriate scope:

* system-wide;
* company;
* provider;
* bank;
* fiscal device;
* user;
* transaction.

Do not introduce global settings for configuration that legitimately varies by Company.

Configuration fields should have clear defaults and should fail explicitly when mandatory configuration is missing.

Settings DocTypes should be preferred over scattered custom fields when a feature has substantial configuration of its own.

## Custom Fields and Property Setters

CSF TZ may extend standard DocTypes using Custom Fields and Property Setters.

Application-owned metadata must be reproducible from source.

Do not rely on production sites containing manually created Custom Fields that are absent from application setup or migration logic.

Field creation must be idempotent.

Before changing or deleting existing fields, account for installations that may already contain data.

Fieldnames should be stable after release wherever possible.

## Data Model

A CSF TZ DocType should exist when a concept has an independent lifecycle, configuration role, transactional role, integration role, or audit requirement.

Do not create a new DocType merely to avoid using an appropriate ERPNext model.

Links to ERPNext documents should use proper Link or Dynamic Link fields wherever possible.

Child tables should be used for records that exist only as part of their parent document.

Integration logs should retain identifiers required to trace the corresponding ERPNext transaction and external transaction.

## Migrations and Patches

Database and metadata migrations are part of the application contract.

Use `patches.txt` for one-time migration work.

Use install or migrate hooks for operations that genuinely need to remain repeatable.

A patch should:

* be safe for existing production data;
* be deterministic;
* preferably be idempotent;
* avoid assumptions about optional modules or data;
* handle already-migrated records safely;
* avoid silently destroying business data;
* complete in reasonable bounded operations.

Do not rewrite the behaviour of a previously released patch after installations may already have executed it.

Create a new patch for subsequent corrections.

Destructive migrations require particular care and should be explicitly documented.

## Installation and Migration Hooks

`after_install` prepares newly installed sites.

`after_migrate` may enforce application-owned metadata or configuration that must remain synchronized.

Do not put expensive recurring business processing in migration hooks.

Migration hooks must not rely on external services being available.

A failed external provider must not prevent a normal `bench migrate` unless that provider is fundamentally required to make the schema valid.

## Version Compatibility

Each maintained branch must explicitly declare the supported Frappe and ERPNext major versions in `pyproject.toml`.

A branch should target a defined framework generation.

Do not make one branch silently support incompatible framework majors through extensive version-condition logic.

Compatibility changes involving:

* controller APIs;
* DocType fields;
* hooks;
* accounting behaviour;
* scheduler behaviour;
* framework APIs;
* JavaScript APIs

must be checked against the targeted Frappe and ERPNext versions.

Upstream APIs should not be assumed stable across major releases.

## Modules

Functional modules should group related business behaviour.

Current module boundaries may include areas such as:

* CSF TZ
* Purchase and Stock Management
* Sales and Marketing
* Meal Count
* Stanbic
* KCB
* VFD Providers
* VFD Settings

New modules should only be introduced when they represent a coherent functional domain.

Do not create a module for every small feature.

## Public Surfaces

The important public surfaces of CSF TZ include:

* DocTypes
* reports
* workspaces
* whitelisted methods
* hooks into ERPNext documents
* scheduled jobs
* integrations consumed by external systems
* configuration DocTypes
* print and Jinja helpers where explicitly exposed

Changes to these surfaces may affect installed sites even when no Python import API changes.

Treat fieldnames, DocType names, integration contracts, and externally consumed endpoints as compatibility-sensitive.

## Permissions and Authorization

Server-side permission checks remain authoritative.

Creating a custom form button does not grant permission to perform the corresponding operation.

APIs that read or modify ERPNext documents must respect Frappe permissions unless the integration explicitly requires privileged system processing.

Any deliberate permission bypass must:

* have a documented reason;
* be scoped narrowly;
* validate the caller or integration;
* avoid accepting arbitrary document access from untrusted input.

## Security Model

CSF TZ runs with the privileges of the Frappe application process and has access to site data.

Application code therefore belongs inside the site's trusted computing boundary.

Assume that server-side CSF TZ code can potentially access:

* accounting information;
* customer and supplier records;
* employee information;
* payroll information;
* integration credentials;
* regulatory records;
* uploaded files.

From this:

* validate untrusted input;
* avoid arbitrary SQL construction;
* avoid arbitrary filesystem access;
* do not execute user-supplied code;
* protect integration credentials;
* restrict guest endpoints;
* validate uploaded files;
* avoid logging unnecessary personal or financial information.

External responses must be treated as untrusted input.

## SQL and Database Access

Prefer Frappe ORM, Query Builder, and standard document APIs.

Direct SQL is acceptable when there is a clear technical reason such as reporting, performance, migration, or functionality not reasonably expressible through supported APIs.

Direct SQL must:

* parameterize dynamic values;
* respect `docstatus` where relevant;
* consider Company boundaries;
* consider permissions when used in user-facing operations;
* avoid direct writes to framework-owned accounting or stock ledgers unless explicitly required by framework architecture.

Database writes should normally occur through document APIs.

## Error Handling

Errors shown to users should explain the business problem and, where possible, the corrective action.

Do not expose raw provider credentials, tokens, SQL, or internal stack details through user-facing errors.

Integration errors should preserve enough technical information in appropriate logs for diagnosis.

Retryable errors should be distinguishable from permanent validation failures.

## Logging and Auditability

Compliance-sensitive and integration-sensitive operations should be traceable.

Where appropriate, preserve:

* source document;
* external reference;
* timestamp;
* provider;
* operation;
* result;
* error;
* retry information.

Do not use unrestricted console output as the primary production logging mechanism.

Use Frappe logging, integration log DocTypes, or purpose-built audit records.

## Cancellation and Reversal

Any feature that creates downstream records must explicitly consider cancellation.

When a source ERPNext document is cancelled, CSF TZ must determine whether downstream records should:

* be cancelled;
* be reversed;
* be unlinked;
* remain as immutable audit evidence;
* trigger an external cancellation;
* require manual intervention.

Cancellation logic must not silently leave active financial or compliance consequences behind.

## Idempotency

Operations that may be retried must protect against duplicate execution.

This particularly applies to:

* scheduled jobs;
* webhook/API callbacks;
* fiscal submissions;
* payment processing;
* bank reconciliation;
* journal creation;
* background jobs;
* authority synchronization.

Where an external system provides a transaction identifier, persist and use it for duplicate detection when practical.

## Performance

Code running in transaction hooks must remain bounded.

Avoid:

* queries inside large loops;
* loading complete tables unnecessarily;
* performing expensive external calls repeatedly;
* processing entire transaction histories during ordinary document validation;
* synchronous bulk processing where a background job is appropriate.

Use batching for high-volume scheduled operations.

Performance optimizations must not compromise accounting or compliance correctness.

## Testing

Business-critical features should have automated tests.

Priority areas include:

* accounting consequences;
* taxation;
* VFD/fiscalization;
* payroll calculations;
* document submission and cancellation;
* integration request/response handling;
* migration patches;
* scheduled job idempotency;
* duplicate prevention.

Tests should exercise business outcomes rather than merely whether a function executes.

Where an external provider is involved, provider calls should normally be mocked in automated tests.

Tests must not depend on live banking, fiscal, payment, or authority services.

## Development Rules

When changing existing functionality:

1. Identify the owning domain.
2. Check existing hooks and overrides before adding another extension point.
3. Reuse ERPNext behaviour where possible.
4. Preserve submission and cancellation semantics.
5. Consider multi-company behaviour.
6. Consider permissions.
7. Consider migration requirements.
8. Consider scheduled or asynchronous execution.
9. Consider integration retry and duplicate behaviour.
10. Add or update tests for material business logic.

Avoid adding unrelated convenience functions to `custom_api.py` or other already broad modules.

New substantial features should use dedicated domain modules.

## Naming

Use names that describe the business concept rather than a customer or temporary implementation.

Provider-specific functionality may use the provider name where the provider itself defines the integration.

Avoid abbreviations unless they are established domain terminology such as VAT, VFD, TRA, PAYE, or NSSF.

Do not encode one customer's name into reusable CSF TZ business logic.

## Source of Truth

For application behaviour:

* Python source is the source of truth for server-side logic.
* JavaScript source is the source of truth for client-side behaviour.
* DocType JSON is the source of truth for application-owned DocType metadata.
* patch modules and migration hooks are the source of truth for migrations.
* `hooks.py` is the source of truth for registered framework extensions and schedules.
* `pyproject.toml` is the source of truth for Python and Frappe/ERPNext compatibility declarations.

Production-site manual customizations are not substitutes for source-controlled application behaviour.

## Contribution Boundary

Before adding functionality to CSF TZ, ask:

**Is this Tanzania-specific or reusable across a substantial number of CSF TZ installations?**

If no, it probably belongs in:

* standard ERPNext configuration;
* another reusable application;
* an industry-specific application; or
* a customer-specific application.

CSF TZ should not become a collection of unrelated customer customizations.

## Documentation Map

Documentation should progressively cover:

* Architecture
* Installation and upgrade
* Tanzanian statutory configuration
* VFD configuration and providers
* Tax and withholding configuration
* Banking integrations
* Payroll localization
* Purchase and import processes
* Scheduled jobs
* API and integration contracts
* Migration and compatibility guidance
* Troubleshooting

`SPEC.md` defines architectural and development rules.

`README.md` should remain the high-level introduction and installation entry point.

Detailed operational and developer documentation should live under `docs/` as the repository grows.
