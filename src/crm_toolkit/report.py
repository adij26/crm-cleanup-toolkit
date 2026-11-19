"""Turn a RunSummary into a Markdown report a RevOps or marketing lead can skim."""

from __future__ import annotations

from .pipeline import RunSummary

FLAG_LABELS = {
    "invalid_email": "Invalid email address",
    "missing_email": "No email address",
    "role_based_email": "Team inbox (info@, sales@…)",
    "personal_email": "Personal email (Gmail, Yahoo…)",
    "disposable_email": "Disposable email domain",
    "fixed_domain_typo": "Email domain typo auto-fixed",
    "invalid_phone": "Phone number couldn't be parsed",
    "missing_company": "No company name",
    "merged_duplicates": "Record built from merged duplicates",
}


def _bar(count: int, total: int, width: int = 20) -> str:
    filled = round(width * count / total) if total else 0
    return "█" * filled + "░" * (width - filled)


def _table(counter, total: int, order: list[str] | None = None) -> str:
    keys = order or [k for k, _ in counter.most_common()]
    lines = ["| | Count | Share | |", "|---|---:|---:|---|"]
    for key in keys:
        count = counter.get(key, 0)
        share = f"{100 * count / total:.0f}%" if total else "0%"
        lines.append(f"| {key} | {count} | {share} | `{_bar(count, total)}` |")
    return "\n".join(lines)


def render_markdown(summary: RunSummary, title: str = "CRM Cleanup Report") -> str:
    s = summary
    pct_dupes = 100 * s.duplicates_removed / s.rows_in if s.rows_in else 0
    needs_review = sum(s.flag_counts.get(f, 0) for f in ("invalid_email", "missing_email", "invalid_phone"))

    out = [
        f"# {title}",
        "",
        "## At a glance",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Rows in | {s.rows_in} |",
        f"| Unique contacts out | {s.rows_out} |",
        f"| Duplicates merged | {s.duplicates_removed} ({pct_dupes:.0f}%) |",
        f"| A-grade leads | {s.grade_counts.get('A', 0)} |",
        f"| Records needing manual review | {needs_review} |",
        "",
        "## Lead grades",
        "",
        _table(s.grade_counts, s.rows_out, ["A", "B", "C", "D"]),
        "",
        "## Data quality issues",
        "",
        "| Issue | Records |",
        "|---|---:|",
    ]
    for flag, count in s.flag_counts.most_common():
        out.append(f"| {FLAG_LABELS.get(flag, flag)} | {count} |")

    out += [
        "",
        "## Who is in the database",
        "",
        "**By seniority**",
        "",
        _table(s.seniority_counts, s.rows_out),
        "",
        "**By function**",
        "",
        _table(s.function_counts, s.rows_out),
        "",
        "## Top 10 leads",
        "",
        "| Score | Grade | Name | Title | Company |",
        "|---:|:---:|---|---|---|",
    ]
    for r in s.top_leads:
        out.append(f"| {r['lead_score']} | {r['lead_grade']} | {r['first_name']} {r['last_name']} "
                   f"| {r['job_title']} | {r['company']} |")

    if s.unmapped_columns:
        out += ["", "## Columns passed over",
                "", "These input columns weren't recognised and were left out of the output: "
                + ", ".join(f"`{c}`" for c in s.unmapped_columns)]
    return "\n".join(out) + "\n"
