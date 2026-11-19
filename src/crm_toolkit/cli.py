"""Command-line entry point: `crm-clean contacts.csv -o clean.csv --report report.md`."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from .pipeline import run
from .report import render_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="crm-clean",
        description="Clean, dedupe and score a CRM contact export (HubSpot, Salesforce or any CSV).",
    )
    parser.add_argument("input", help="path to the exported contacts CSV")
    parser.add_argument("-o", "--output", default="clean_contacts.csv", help="where to write the cleaned CSV")
    parser.add_argument("-r", "--report", help="optional path for a Markdown summary report")
    parser.add_argument("-c", "--config", help="custom scoring rules (TOML); defaults to the built-in ICP")
    parser.add_argument("--as-of", help="score recency as of this date (YYYY-MM-DD); defaults to today")
    args = parser.parse_args(argv)

    if not Path(args.input).exists():
        print(f"error: {args.input} not found", file=sys.stderr)
        return 1

    today = date.fromisoformat(args.as_of) if args.as_of else None
    summary = run(args.input, args.output, args.config, today=today)

    print(f"✓ {summary.rows_in} rows in → {summary.rows_out} unique contacts "
          f"({summary.duplicates_removed} duplicates merged)")
    print(f"  Grades: " + "  ".join(f"{g}={summary.grade_counts.get(g, 0)}" for g in "ABCD"))
    print(f"  Cleaned file: {args.output}")
    if args.report:
        Path(args.report).write_text(render_markdown(summary), encoding="utf-8")
        print(f"  Report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
