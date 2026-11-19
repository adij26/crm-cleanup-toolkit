"""Find and merge duplicate contacts.

Two records are treated as the same person when either
  1. they share an email address, or
  2. they share a full name AND the same company (by name or email domain).

Merging keeps the most complete record: the first non-empty value wins for
text fields, the highest value wins for engagement counts, and the most recent
date wins for last activity.
"""

from __future__ import annotations

from .normalize import FREE_EMAIL_DOMAINS, company_key, email_domain, normalize_email, normalize_phone

# Flags that describe a single field value; they are recomputed after a merge
# so a bad phone on one duplicate does not stick if another had a good one.
FIELD_FLAGS = {"invalid_email", "missing_email", "role_based_email", "personal_email",
               "disposable_email", "invalid_phone"}

NUMERIC_MAX_FIELDS = {"email_opens", "page_views", "company_size"}
DATE_MAX_FIELDS = {"last_activity_date"}


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def _match_keys(record: dict) -> list[str]:
    keys = []
    email = record.get("email", "")
    if email and "invalid_email" not in record.get("flags", []):
        keys.append("email:" + email)

    first = record.get("first_name", "").lower()
    last = record.get("last_name", "").lower()
    if first and last:
        org = company_key(record.get("company", ""))
        if org:
            keys.append(f"name+co:{first} {last}|{org}")
        domain = email_domain(email)
        if domain and domain not in FREE_EMAIL_DOMAINS:
            keys.append(f"name+domain:{first} {last}|{domain}")
    return keys


def _to_number(value) -> float:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _completeness(record: dict) -> int:
    return sum(1 for k, v in record.items() if k != "flags" and str(v).strip())


def merge_group(records: list[dict]) -> dict:
    # Start from the most complete record so its values take priority.
    ordered = sorted(records, key=_completeness, reverse=True)
    merged = dict(ordered[0])
    flags = set()
    for rec in ordered:
        flags.update(rec.get("flags", []))
        for field, value in rec.items():
            if field == "flags":
                continue
            current = merged.get(field, "")
            if field in NUMERIC_MAX_FIELDS:
                if _to_number(value) > _to_number(current):
                    merged[field] = value
            elif field in DATE_MAX_FIELDS:
                if str(value) > str(current):  # ISO dates sort as strings
                    merged[field] = value
            elif field == "phone":
                # prefer a phone that parsed cleanly (normalized ones start with +)
                if str(value).startswith("+") and not str(current).startswith("+"):
                    merged[field] = value
            elif not str(current).strip() and str(value).strip():
                merged[field] = value
    if len(records) > 1:
        flags -= FIELD_FLAGS
        flags.update(normalize_email(merged.get("email"))[1])
        flags.update(normalize_phone(merged.get("phone"))[1])
        flags.add("merged_duplicates")
    merged["flags"] = sorted(flags)
    merged["merged_count"] = len(records)
    merged["source_ids"] = ";".join(sorted(str(r.get("record_id", "")) for r in records))
    return merged


def dedupe(records: list[dict]) -> tuple[list[dict], int]:
    """Return (unique_records, duplicates_removed)."""
    uf = _UnionFind(len(records))
    seen: dict[str, int] = {}
    for i, rec in enumerate(records):
        for key in _match_keys(rec):
            if key in seen:
                uf.union(seen[key], i)
            else:
                seen[key] = i

    groups: dict[int, list[dict]] = {}
    for i, rec in enumerate(records):
        groups.setdefault(uf.find(i), []).append(rec)

    unique = [merge_group(group) for _, group in sorted(groups.items())]
    return unique, len(records) - len(unique)
