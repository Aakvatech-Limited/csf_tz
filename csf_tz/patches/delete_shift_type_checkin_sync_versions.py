"""Delete `Version` rows that only record a `last_sync_of_checkin` bump.

The biometric checkin sync PUTs `last_sync_of_checkin` on every run, so before
`csf_tz.csftz_hooks.shift_type` started setting `ignore_version` each sync left a `Version`
row behind. They record only bookkeeping, and on a busy site they are the bulk of
`tabVersion`.

Not in `patches.txt` — deleting history is a judgement call, so it is invoked deliberately.
Run `estimate` first; it only reads.

    bench --site <site> execute csf_tz.patches.delete_shift_type_checkin_sync_versions.estimate
    bench --site <site> execute csf_tz.patches.delete_shift_type_checkin_sync_versions.execute
    bench --site <site> execute csf_tz.patches.delete_shift_type_checkin_sync_versions.reclaim_space

Safe on a 70M-row table: `ref_doctype` is indexed, so the work is proportional to the Shift
Type slice, not the table. Deletes go in small autocommitted batches, and an interrupted run
resumes — rows are matched by content, so nothing is revisited.

Matching happens in Python, where it can be precise across frappe versions; JSON parsing is
not the bottleneck (~3 us/row). Measured 7k-13k rows/s deleting locally — under two hours
for 35M rows, but that is one bench, not a promise.

DELETEs alone only mark pages reusable inside the tablespace — the file does not shrink.
`reclaim_space` rebuilds the table to return it to the filesystem; it is optional, runs long
on a big table, and needs free disk for a second copy, so run it in a quiet window.
"""

import json

import frappe

DOCTYPE = "Shift Type"
SYNC_FIELD = "last_sync_of_checkin"

# Read in pages this size, delete in statements this size. Small enough that each
# transaction is short-lived under live traffic.
BATCH_SIZE = 2_500
LOG_EVERY = 100_000

# The only SQL-side narrowing: a Version that never mentions the field cannot be a sync
# row. Safe because `is_checkin_sync_only` implies it, so the two can never disagree.
#
# `length(data) < 250` and `data not like '%],[%'` were tried and dropped. The length bound
# had no counterpart in Python and so was the only predicate able to change the answer —
# sync-only payloads longer than the bound were silently skipped (verified: 50 such rows
# survived it). The `],[` test was redundant. Neither cost anything to remove; the run
# measured no slower without them.
DATA_LIKE = f"%{SYNC_FIELD}%"


def execute():
    """Delete every checkin-sync-only Version row for Shift Type."""
    deleted = delete_sync_versions()
    if not deleted:
        return

    print(f"\nDeleted {deleted} rows.")

    # ANALYZE (~20 ms) first: stats lag badly after a bulk delete, enough that on 200k rows
    # `data_length` briefly reported 10 MB *more* than before it.
    frappe.db.sql("analyze table tabVersion")
    print(table_space())
    print("The file itself does not shrink until the table is rebuilt: reclaim_space().")


def estimate():
    """Report what `execute` would delete, without writing anything."""
    total = 0
    matched = 0
    matched_bytes = 0
    total_bytes = 0

    for batch in scan():
        total += len(batch)
        total_bytes += sum(len(row.data or "") for row in batch)
        for row in batch:
            if is_checkin_sync_only(row.data):
                matched += 1
                matched_bytes += len(row.data or "")

        if total % LOG_EVERY < BATCH_SIZE:
            print(f"  scanned {total}, matched {matched}")

    print(
        f"\n{DOCTYPE}: {matched} of {total} Version rows are {SYNC_FIELD}-only "
        f"({round(matched_bytes / 1024**2, 1)} MB of {round(total_bytes / 1024**2, 1)} MB scanned)"
    )
    # No table_space() here: nothing was written, so it would only show the current size,
    # which says nothing about what the cleanup would free. `matched_mb` is that estimate.

    return {"scanned": total, "matched": matched, "matched_mb": round(matched_bytes / 1024**2, 1)}


def delete_sync_versions():
    """Walk this doctype's Version rows, deleting the sync-only ones.

    Pagination is by keyset on `name` rather than OFFSET, so each batch resumes from the
    last key instead of re-counting rows it has already passed.
    """
    scanned = 0
    deleted = 0

    for batch in scan():
        scanned += len(batch)
        doomed = [row.name for row in batch if is_checkin_sync_only(row.data)]

        if doomed:
            # By primary key — Version rows are immutable, so no need to re-check payloads.
            frappe.db.delete("Version", {"name": ("in", doomed)})
            deleted += len(doomed)

        # Commit even when nothing was deleted. Under REPEATABLE READ with autocommit off,
        # the SELECT holds a read view until commit — skipping it would walk a long
        # non-matching stretch under one snapshot, pinning undo history and hiding
        # concurrent writes from the rest of the scan.
        frappe.db.commit()

        if scanned % LOG_EVERY < BATCH_SIZE:
            print(f"  scanned {scanned}, deleted {deleted}")

    print(f"{DOCTYPE}: deleted {deleted} of {scanned} Version rows scanned")

    return deleted


def scan():
    """Yield batches of this doctype's candidate Version rows, ordered by primary key.

    Keyed on `name` alone: it is unique, whereas `docname` is neither unique nor non-null,
    so a row-value keyset on it would compare against NULL and skip rows forever.

    Paging on `(docname, name)` to follow `(ref_doctype, docname)` measures ~13x slower —
    few distinct docnames means each batch rescans a growing prefix (28 ms vs 366 ms
    mid-walk, 150k rows). Don't re-derive this from EXPLAIN: it ranked them backwards on an
    empty slice and showed both as equivalent once populated. Only timing settled it.

    No streaming cursor: it would hold one result set open all run, and `frappe.db.commit()`
    issues its COMMIT on that same cursor, breaking the connection mid-stream.
    """
    last_name = ""

    while True:
        batch = frappe.db.sql(
            """select name, data from tabVersion
            where ref_doctype = %s
                and name > %s
                and data like %s
            order by name
            limit %s""",
            (DOCTYPE, last_name, DATA_LIKE, BATCH_SIZE),
            as_dict=True,
        )
        if not batch:
            return

        # Advance the cursor before yielding: the caller may delete these rows, so the
        # keyset must not depend on them still existing.
        last_name = batch[-1].name

        yield batch


def is_checkin_sync_only(data: str) -> bool:
    """True if this Version records nothing but a `last_sync_of_checkin` change.

    Parsed, not pattern-matched: a `LIKE` cannot express "and nothing else changed", and the
    key-set varies by writing frappe version (v11 four keys, v15 six, bare `{"changed"}`
    also occurs). So rather than listing keys that must be empty, require that `changed`
    holds only our field and no other key carries a value — an unknown key with content
    means the row records something unrecognised, so it is kept.
    """
    if not data:
        return False

    try:
        payload = json.loads(data)
    except ValueError:
        return False

    if not isinstance(payload, dict):
        return False

    changed = payload.get("changed")
    if not isinstance(changed, list) or len(changed) != 1:
        return False

    entry = changed[0]
    if not isinstance(entry, (list, tuple)) or not entry or entry[0] != SYNC_FIELD:
        return False

    # Every other key must be empty or null, whatever it is called — this is what keeps the
    # check version-agnostic.
    return not any(value for key, value in payload.items() if key != "changed")


def table_space() -> str:
    """On-disk size of tabVersion and how much is reusable but not yet returned.

    Needs no special grants: `information_schema.tables` filters to tables the connection
    can see rather than requiring a global privilege. (Unlike `innodb_trx`, which needs
    PROCESS and raises for a site user.) A missing table yields no rows, hence the guard.
    """
    row = frappe.db.sql(
        """select round(data_length/1024/1024, 1), round(data_free/1024/1024, 1)
        from information_schema.tables
        where table_schema = database() and table_name = 'tabVersion'"""
    )
    if not row:
        return ""

    data_mb, free_mb = row[0]

    return f"tabVersion: {data_mb} MB on disk, {free_mb} MB reported free"


def _table_size_mb() -> float:
    """Just the on-disk size, for before/after comparison."""
    row = frappe.db.sql(
        """select data_length/1024/1024 from information_schema.tables
        where table_schema = database() and table_name = 'tabVersion'"""
    )

    return float(row[0][0]) if row else 0.0


def reclaim_space():
    """Rebuild tabVersion so space freed by the deletes returns to the filesystem.

    DELETEs only mark pages reusable inside the tablespace; the file does not shrink.
    `ALTER TABLE ... FORCE` writes a fresh, densely packed tablespace and unlinks the
    old one.

    `LOCK=NONE` is a safety mechanism, not an optimisation: MariaDB refuses the
    statement outright if it cannot rebuild while writes continue, so the worst case is
    a skipped table rather than an outage. `ALGORITHM=INPLACE` likewise refuses rather
    than silently falling back to a blocking copy.

    Needs no elevated grants — `ALTER` on the table is enough and nothing here sets a
    global variable. If the 128 MB `innodb_online_alter_log_max_size` default overflows
    mid-rebuild, the ALTER rolls back with the table untouched; raising it needs SUPER.

    Scales with table size and needs free disk for a second copy, so prefer a quiet window
    (24s for 350 MB here; a 70M-row table will be far longer).
    """
    print(table_space(), "- rebuilding")
    before = _table_size_mb()

    try:
        frappe.db.sql_ddl("alter table `tabVersion` force, algorithm=inplace, lock=none")
    except Exception as e:
        print(f"  !! SKIPPED: {e}")
        print("  !! table unchanged and safe; rows are deleted but the file did not shrink.")
        return

    # ANALYZE is ~20 ms (InnoDB samples 20 index pages, so it does not scale with the
    # table) and without it the "after" size is stale enough to read as growth.
    frappe.db.sql("analyze table tabVersion")
    after = _table_size_mb()
    reclaimed = before - after
    print(f"  {before:.1f} MB -> {after:.1f} MB", end="")
    print(f" (reclaimed {reclaimed:.1f} MB)" if reclaimed > 0 else " (nothing to reclaim)")
