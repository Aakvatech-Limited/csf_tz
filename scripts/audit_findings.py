#!/usr/bin/env python3
"""Import and reconcile Frappe Cloud Semgrep findings without silent deletions.

Usage:
  python scripts/audit_findings.py import baseline.json --kind security
  python scripts/audit_findings.py import correctness.json --kind correctness
  python scripts/audit_findings.py reconcile latest.json --kind security
  python scripts/audit_findings.py check
The import file must be a Semgrep JSON report with a 'results' list.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "audit" / "frappecloud_findings.csv"
FIELDS = [
    "finding_id", "category", "rule_id", "file", "line", "message",
    "original_fingerprint", "status", "disposition", "pr", "commit",
    "test_evidence", "reviewer", "review_date", "notes", "last_seen",
]
CATEGORIES = {"security": 76, "correctness": 421}
FINAL = {"fixed", "false_positive", "accepted_risk", "superseded"}
OPEN = {"open", "in_progress", "needs_review"}


def load():
    if not REGISTER.exists():
        return []
    with REGISTER.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(rows):
    REGISTER.parent.mkdir(parents=True, exist_ok=True)
    with REGISTER.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["category"], r["finding_id"])))


def findings(path, kind):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw.get("results"), list):
        raise SystemExit("Expected Semgrep JSON with a results array")
    seen = Counter()
    for item in raw["results"]:
        file = item.get("path", "").replace("\\", "/")
        rule = item.get("check_id", "")
        line = str(item.get("start", {}).get("line", ""))
        message = item.get("extra", {}).get("message", "")
        # Semgrep fingerprints are preferred; fallback preserves duplicates by occurrence.
        fingerprint = item.get("extra", {}).get("fingerprint", "")
        if not fingerprint:
            basis = json.dumps([kind, rule, file, line, message], ensure_ascii=False)
            fingerprint = hashlib.sha256(basis.encode()).hexdigest()[:24]
        seen[fingerprint] += 1
        unique_key = f"{kind}:{fingerprint}:{seen[fingerprint]}"
        stable_id = hashlib.sha256(unique_key.encode()).hexdigest()[:16]
        yield {
            "finding_id": f"FC-{kind[0].upper()}-{stable_id}",
            "category": kind,
            "rule_id": rule,
            "file": file,
            "line": line,
            "message": message.replace("\n", " "),
            "original_fingerprint": unique_key,
        }


def import_baseline(path, kind):
    rows = load()
    incoming = list(findings(path, kind))
    if any(r["category"] == kind for r in rows):
        raise SystemExit(f"{kind} baseline already exists; do not replace it. Use reconcile.")
    for finding in incoming:
        rows.append({**dict.fromkeys(FIELDS, ""), **finding, "status": "open", "last_seen": "baseline"})
    save(rows)
    print(f"Imported {len(incoming)} {kind} findings. Expected original count: {CATEGORIES[kind]}.")
    if len(incoming) != CATEGORIES[kind]:
        raise SystemExit("Baseline count mismatch: verify report version and scope; rows retained for investigation.")


def reconcile(path, kind):
    rows = load()
    incoming = list(findings(path, kind))
    indexed = {r["original_fingerprint"]: r for r in rows if r["category"] == kind}
    present = set()
    for finding in incoming:
        key = finding["original_fingerprint"]
        present.add(key)
        if key in indexed:
            row = indexed[key]
            row["last_seen"] = "present"
            if row["status"] in FINAL:
                row["status"] = "needs_review"
                row["notes"] += " | Reappeared in latest scan; revalidate prior disposition."
        else:
            row = {**dict.fromkeys(FIELDS, ""), **finding, "status": "open",
                   "last_seen": "new"}
            rows.append(row)
    for key, row in indexed.items():
        if key not in present:
            row["last_seen"] = "absent"
            if row["status"] not in FINAL:
                row["status"] = "needs_review"
                row["notes"] += " | Absent from new scan; confirm cause before closing."
    save(rows)
    print(f"Reconciled {len(incoming)} current {kind} warnings, retaining all historic findings.")


def check():
    rows = load()
    errors = []
    ids = [r["finding_id"] for r in rows]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate finding IDs")
    for kind, expected in CATEGORIES.items():
        baseline_count = sum(r["category"] == kind and r["last_seen"] != "new" for r in rows)
        if baseline_count < expected:
            errors.append(f"{kind}: only {baseline_count}/{expected} original findings imported")
    for row in rows:
        if row["status"] not in OPEN | FINAL:
            errors.append(f"{row['finding_id']}: invalid status")
        if row["status"] in FINAL:
            required = ["disposition", "reviewer", "review_date", "notes"]
            if row["status"] == "fixed":
                required += ["pr", "test_evidence"]
            for field in required:
                if not row[field].strip():
                    errors.append(f"{row['finding_id']}: {field} required for {row['status']}")
    print(f"Tracked: {len(rows)}; status: {dict(Counter(r['status'] for r in rows))}")
    for error in errors:
        print("FAIL:", error)
    if errors:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["import", "reconcile", "check"])
    parser.add_argument("report", nargs="?")
    parser.add_argument("--kind", choices=CATEGORIES)
    args = parser.parse_args()
    if args.command == "check":
        check()
    elif not args.report or not args.kind:
        parser.error("import and reconcile require a report and --kind")
    elif args.command == "import":
        import_baseline(args.report, args.kind)
    else:
        reconcile(args.report, args.kind)


if __name__ == "__main__":
    main()
