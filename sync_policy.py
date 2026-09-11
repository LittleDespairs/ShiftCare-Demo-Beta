"""Portable, three-way organization sync using stable record identities.

Numeric database IDs and audit timestamps are transport details. A baseline is
the last snapshot accepted by both peers; absence in a newer snapshot therefore
represents a deletion, rather than an invitation to resurrect an old record.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import json
import re


RELATIONS = {
    "positions": {"department_id": "departments"},
    "shift_templates": {"position_id": "positions"},
    "shift_requirements": {"position_id": "positions"},
    "coverage_requirements": {"position_id": "positions"},
    "employee_preferences": {"employee_id": "employees"},
    "employee_week_preferences": {"employee_id": "employees"},
    "employee_week_preference_requests": {"employee_id": "employees"},
    "employee_recurring_preferences": {"employee_id": "employees"},
    "employee_day_statuses": {"employee_id": "employees"},
    "employee_positions": {"employee_id": "employees", "position_id": "positions"},
    "schedule_entries": {
        "employee_id": "employees", "position_id": "positions", "shift_template_id": "shift_templates",
    },
    "shift_swap_requests": {
        "requester_employee_id": "employees", "target_employee_id": "employees",
        "requester_schedule_entry_id": "schedule_entries", "target_schedule_entry_id": "schedule_entries",
    },
}
AUDIT_FIELDS = {
    "id", "organization_id", "created_at", "updated_at", "updated_by", "reviewed_by",
    "imported_at", "last_verified_at",
}


class SyncConflict(ValueError):
    """Neither side may silently discard the other side's changes."""


def bootstrap_legacy_remote_additions(local: dict, remote: dict, remote_bundle: dict, evidence: dict) -> dict:
    """Adopt a legacy baseline only for provably new incoming weekly requests.

    An absent baseline cannot distinguish a deletion from a missing record.
    Therefore local-only rows, edited shared rows, changed catalog/settings,
    destructive outbox history and older remote-only rows require review.
    This deliberately never unions arbitrary snapshots or chooses a winner.
    """
    def reject():
        raise SyncConflict("Sync needs review: these different copies have no agreed baseline; changes were preserved")

    def timestamp(value):
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
        except (TypeError, ValueError):
            return None

    cutoff = timestamp(evidence.get("last_push_at"))
    if cutoff is None or local.get("organization") != remote.get("organization"):
        reject()
    local_records = local.get("records", {})
    remote_records = remote.get("records", {})
    for change in evidence.get("outbox", []):
        if change.get("operation") != "upsert":
            reject()
        if change.get("status") in {"pending", "failed", "syncing"}:
            if change.get("entity_public_id") not in local_records.get(change.get("entity_type"), {}):
                reject()
    allowed_additions = {"employee_week_preferences", "employee_week_preference_requests"}
    raw_remote = {
        table: {str(row.get("public_id")): row for row in rows}
        for table, rows in (remote_bundle.get("records") or {}).items()
    }
    for table in set(local_records) | set(remote_records):
        ours, theirs = local_records.get(table, {}), remote_records.get(table, {})
        if any(key not in theirs or value != theirs[key] for key, value in ours.items()):
            reject()
        additions = set(theirs) - set(ours)
        if additions and table not in allowed_additions:
            reject()
        for key in additions:
            created = timestamp(raw_remote.get(table, {}).get(key, {}).get("created_at"))
            if created is None or created <= cutoff:
                reject()
    # Run the ordinary referential checks too; malformed additions must not
    # cause an importer to drop a request whose employee is unavailable.
    return merge_snapshots(local, local, remote)


class StableIdentityImportCursor:
    """Keep destination IDs when a replace import recreates the same records.

    Only static INSERT statements issued by our import routines are adapted;
    identity comes from the destination database, never from a supplied ID.
    This keeps open clients and surviving foreign-key links valid after sync.
    """
    def __init__(self, cursor, existing_rows: dict):
        self.cursor = cursor
        self.existing_rows = existing_rows
        self.lastrowid = None

    def __getattr__(self, name):
        return getattr(self.cursor, name)

    def execute(self, statement, params=()):
        preserved_id = None
        match = re.search(r"INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*\(", statement, re.IGNORECASE)
        if match:
            table = match.group(1)
            columns = [column.strip() for column in match.group(2).split(",")]
            identity_column = "license_id" if table == "licenses" else "public_id"
            if identity_column in columns and "id" not in columns:
                identity = params[columns.index(identity_column)]
                previous = self.existing_rows.get(table, {}).get(identity)
                if previous:
                    preserved_id = previous["id"]
                    params = list(params)
                    if "created_at" in columns and previous.get("created_at"):
                        params[columns.index("created_at")] = previous["created_at"]
                    if "reviewed_by" in columns and "status" in columns:
                        if params[columns.index("status")] == previous.get("status"):
                            params[columns.index("reviewed_by")] = previous.get("reviewed_by")
                    statement = (
                        statement[:match.start(2)] + "id, " + statement[match.start(2):match.end()]
                        + "?, " + statement[match.end():]
                    )
                    params.insert(0, previous["id"])
        self.cursor.execute(statement, params)
        self.lastrowid = preserved_id if preserved_id is not None else self.cursor.lastrowid
        return self


def canonical_snapshot(bundle: dict) -> dict:
    records = bundle.get("records") or {}
    identities = {
        table: {row.get("id"): str(row["public_id"]) for row in rows if row.get("public_id")}
        for table, rows in records.items()
    }
    snapshot = {"organization": {"name": (bundle.get("organization") or {}).get("name", "")}, "records": {}}
    for table, rows in records.items():
        normalized = {}
        for row in rows:
            value = {key: deepcopy(item) for key, item in row.items() if key not in AUDIT_FIELDS}
            for field, target in RELATIONS.get(table, {}).items():
                public_field = field[:-3] + "_public_id"
                public_id = row.get(public_field) or identities.get(target, {}).get(row.get(field))
                if row.get(field) is not None and not public_id:
                    raise SyncConflict(f"Missing stable reference: {table}.{field}")
                value.pop(field, None)
                value[public_field] = public_id
            if table == "employee_positions":
                key = str(value.get("employee_public_id")) + ":" + str(value.get("position_public_id"))
            else:
                key = str(value.get("public_id") or value.get("license_id") or value.get("key") or "")
            if not key or key in normalized:
                raise SyncConflict(f"Missing or duplicate stable identity in {table}")
            normalized[key] = value
        snapshot["records"][table] = normalized
    return snapshot


def snapshot_revision(snapshot: dict) -> str:
    payload = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def merge_snapshots(baseline: dict | None, local: dict, remote: dict) -> dict:
    """Merge independent edits and deletions; reject competing edits to a row."""
    if baseline is None and local != remote:
        raise SyncConflict("Sync needs review: these different copies have no agreed baseline; changes were preserved")
    baseline = baseline or {"organization": {}, "records": {}}
    merged = {"organization": {}, "records": {}}
    conflicts = []

    def choose(before, ours, theirs, label):
        if ours == theirs or theirs == before:
            return deepcopy(ours)
        if ours == before:
            return deepcopy(theirs)
        conflicts.append(label)
        return None

    merged["organization"] = choose(
        baseline.get("organization"), local.get("organization"), remote.get("organization"), "organization",
    )
    tables = set(baseline.get("records", {})) | set(local.get("records", {})) | set(remote.get("records", {}))
    for table in sorted(tables):
        before = baseline.get("records", {}).get(table, {})
        ours = local.get("records", {}).get(table, {})
        theirs = remote.get("records", {}).get(table, {})
        merged["records"][table] = {}
        for key in sorted(set(before) | set(ours) | set(theirs)):
            row = choose(before.get(key), ours.get(key), theirs.get(key), f"{table}:{key}")
            if row is not None:
                merged["records"][table][key] = row
    if conflicts:
        raise SyncConflict("Sync conflict; both copies changed: " + ", ".join(conflicts[:8]))
    # A parent deletion competing with a new child is a conflict too. Never let
    # the database cascade silently remove a newly submitted preference/swap.
    for table, relations in RELATIONS.items():
        for row in merged["records"].get(table, {}).values():
            for field, target in relations.items():
                public_id = row.get(field[:-3] + "_public_id")
                if public_id and public_id not in merged["records"].get(target, {}):
                    raise SyncConflict(f"Sync conflict; deleted {target} is still referenced by {table}")
    return merged


def bundle_from_snapshot(snapshot: dict, source: dict) -> dict:
    """Allocate transport IDs consistently across records from both databases."""
    bundle = {key: deepcopy(value) for key, value in source.items() if key not in {"records", "sync", "sync_revision"}}
    bundle.setdefault("organization", {}).update(snapshot["organization"])
    id_maps = {
        table: {key: index + 1 for index, key in enumerate(sorted(rows))}
        for table, rows in snapshot["records"].items()
    }
    bundle["records"] = {}
    for table, rows in snapshot["records"].items():
        bundle["records"][table] = []
        for key, original in sorted(rows.items()):
            row = deepcopy(original)
            if table not in {"employee_positions", "app_settings"}:
                row["id"] = id_maps[table][key]
            for field, target in RELATIONS.get(table, {}).items():
                public_id = row.get(field[:-3] + "_public_id")
                row[field] = id_maps[target].get(public_id) if public_id else None
            bundle["records"][table].append(row)
    return bundle
