"""End-to-end pipeline: read CSV -> map columns -> clean -> dedupe -> score -> write."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import normalize as n
from .dedupe import dedupe
from .scoring import load_config, score_lead

# Header names seen in HubSpot, Salesforce and spreadsheet exports, mapped to
# the toolkit's internal field names. Matching ignores case, spaces and _.
COLUMN_ALIASES = {
    "record_id": ["record id", "id", "contact id", "lead id"],
    "first_name": ["first name", "firstname", "given name", "first"],
    "last_name": ["last name", "lastname", "surname", "family name", "last"],
    "full_name": ["name", "full name", "contact name"],
    "email": ["email", "email address", "e-mail", "work email"],
    "phone": ["phone", "phone number", "mobile", "mobile phone", "work phone"],
    "company": ["company", "company name", "account", "account name", "organization"],
    "job_title": ["job title", "title", "position", "role"],
    "company_size": ["company size", "number of employees", "employees", "headcount"],
    "country": ["country", "country/region", "country region"],
    "lifecycle_stage": ["lifecycle stage", "lead status", "status", "stage"],
    "lead_source": ["lead source", "original source", "source"],
    "email_opens": ["email opens", "marketing emails opened", "opens"],
    "page_views": ["page views", "number of pageviews", "pageviews", "web visits"],
    "last_activity_date": ["last activity date", "last activity", "last engagement date"],
}

OUTPUT_FIELDS = [
    "record_id", "first_name", "last_name", "email", "phone", "company", "job_title",
    "seniority", "function", "company_size", "country", "lifecycle_stage", "lead_source",
    "email_opens", "page_views", "last_activity_date",
    "lead_score", "lead_grade", "score_reasons", "flags", "merged_count", "source_ids",
]


def _squash(header: str) -> str:
    return "".join(ch for ch in header.lower() if ch.isalnum())


def map_columns(headers: list[str]) -> dict[str, str]:
    """Return {internal_field: original_header} for every header we recognise."""
    lookup = {}
    for internal, aliases in COLUMN_ALIASES.items():
        for alias in [internal, *aliases]:
            lookup.setdefault(_squash(alias), internal)
    mapping = {}
    for header in headers:
        internal = lookup.get(_squash(header))
        if internal and internal not in mapping:
            mapping[internal] = header
    return mapping


def clean_record(raw: dict, mapping: dict[str, str]) -> dict:
    get = lambda f: raw.get(mapping.get(f, ""), "") or ""  # noqa: E731
    flags: list[str] = []

    first, last = get("first_name"), get("last_name")
    if not (first or last) and get("full_name"):
        parts = n.clean_whitespace(get("full_name")).split(" ")
        first, last = parts[0], " ".join(parts[1:])

    email, email_flags = n.normalize_email(get("email"))
    flags += email_flags
    phone, phone_flags = n.normalize_phone(get("phone"))
    flags += phone_flags
    title = n.normalize_title(get("job_title"))

    company = n.normalize_company(get("company"))
    if not company:
        flags.append("missing_company")

    return {
        "record_id": n.clean_whitespace(get("record_id")),
        "first_name": n.normalize_name(first),
        "last_name": n.normalize_name(last),
        "email": email,
        "phone": phone,
        "company": company,
        "job_title": title,
        "seniority": n.classify_seniority(title),
        "function": n.classify_function(title),
        "company_size": n.clean_whitespace(get("company_size")).replace(",", ""),
        "country": n.clean_whitespace(get("country")),
        "lifecycle_stage": n.normalize_stage(get("lifecycle_stage")),
        "lead_source": n.clean_whitespace(get("lead_source")),
        "email_opens": n.clean_whitespace(get("email_opens")) or "0",
        "page_views": n.clean_whitespace(get("page_views")) or "0",
        "last_activity_date": n.clean_whitespace(get("last_activity_date"))[:10],
        "flags": flags,
    }


@dataclass
class RunSummary:
    rows_in: int = 0
    rows_out: int = 0
    duplicates_removed: int = 0
    unmapped_columns: list[str] = field(default_factory=list)
    flag_counts: Counter = field(default_factory=Counter)
    grade_counts: Counter = field(default_factory=Counter)
    seniority_counts: Counter = field(default_factory=Counter)
    function_counts: Counter = field(default_factory=Counter)
    top_leads: list[dict] = field(default_factory=list)


def run(input_path: str | Path, output_path: str | Path, config_path: str | Path | None = None,
        today: date | None = None) -> RunSummary:
    config = load_config(config_path)
    with open(input_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        headers = reader.fieldnames or []
        raw_rows = list(reader)

    mapping = map_columns(headers)
    summary = RunSummary(rows_in=len(raw_rows))
    summary.unmapped_columns = [h for h in headers if h not in mapping.values()]

    cleaned = [clean_record(row, mapping) for row in raw_rows]
    for i, rec in enumerate(cleaned, start=1):
        rec["record_id"] = rec["record_id"] or f"row-{i}"

    unique, removed = dedupe(cleaned)
    summary.duplicates_removed = removed

    for rec in unique:
        score, grade, reasons = score_lead(rec, config, today=today)
        rec["lead_score"], rec["lead_grade"] = score, grade
        rec["score_reasons"] = "; ".join(reasons)

    unique.sort(key=lambda r: r["lead_score"], reverse=True)
    summary.rows_out = len(unique)
    for rec in unique:
        summary.flag_counts.update(rec["flags"])
        summary.grade_counts[rec["lead_grade"]] += 1
        summary.seniority_counts[rec["seniority"]] += 1
        summary.function_counts[rec["function"]] += 1
    summary.top_leads = unique[:10]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for rec in unique:
            writer.writerow({**rec, "flags": ";".join(rec["flags"])})
    return summary
