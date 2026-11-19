# CRM Cleanup & Lead Scoring Toolkit

[![CI](https://github.com/adij26/crm-cleanup-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/adij26/crm-cleanup-toolkit/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

**Turn a messy CRM export into a clean, deduplicated, scored contact list in one command.**

Every marketing and RevOps team has the same problem: list uploads, form fills and event
scans pile up in HubSpot or Salesforce until the database is full of `JOHN SMITH` and
`john smith`, `info@` inboxes, `gmial.com` typos and phone numbers in six formats. Bad data
breaks routing, inflates contact-tier costs and makes lead scoring meaningless.

This toolkit fixes that before the data goes back into the CRM.

```
$ crm-clean data/sample_hubspot_export.csv -o clean.csv -r report.md
✓ 258 rows in → 210 unique contacts (48 duplicates merged)
  Grades: A=45  B=97  C=58  D=10
  Cleaned file: clean.csv
  Report: report.md
```

## What it does

| Step | What happens | Example |
|---|---|---|
| **Map columns** | Recognises HubSpot, Salesforce and spreadsheet headers automatically | `Number of Employees` → `company_size` |
| **Clean fields** | Fixes casing, whitespace, phone formats, legal suffixes, title abbreviations | `ACME, Inc.` → `Acme` · `(415) 555-0134` → `+14155550134` |
| **Flag problems** | Marks invalid, personal, role-based and disposable emails; fixes common domain typos | `maya@gmial.com` → `maya@gmail.com` + flag |
| **Classify titles** | Derives seniority and function from free-text job titles | `Sr. Director of FP&A` → Director · Finance |
| **Merge duplicates** | Matches on email *or* name + company/domain, keeps the most complete and most recent data | 3 records → 1, highest engagement kept |
| **Score leads** | Transparent 0–100 score and A–D grade from rules you control | `+30 seniority: C-Level; +25 function: Finance; …` |
| **Report** | Markdown summary of data quality, grade mix and top leads | [see sample report](examples/output/report.md) |

## Quick start

```bash
git clone https://github.com/adij26/crm-cleanup-toolkit.git
cd crm-cleanup-toolkit
pip install -e .

crm-clean data/sample_hubspot_export.csv -o clean.csv -r report.md
```

To use your own data, export contacts from your CRM as CSV and point the command at it.
No API keys, no dependencies beyond Python 3.11+.

## Customise the scoring

Scoring is rules-based on purpose. A sales team can read the rules, argue with
them and change them without a data scientist. Every row in the output has a
`score_reasons` column that explains exactly where its points came from.

The default rules ([`default_scoring.toml`](src/crm_toolkit/default_scoring.toml)) are tuned
for a B2B finance-software company selling into the Office of the CFO. To fit your own
ideal customer profile, copy the file, change the numbers and pass it in:

```toml
[weights.function]
"Finance" = 25
"Operations" = 15
"Marketing" = 4

[penalties]
personal_email = -5
role_based_email = -10
```

```bash
crm-clean contacts.csv -o clean.csv --config my_icp.toml
```

## How duplicates are matched

Two records are treated as the same person if they share:

1. the same email address (case and whitespace ignored), **or**
2. the same full name **and** the same company (legal suffixes ignored) or the same work-email domain.

Matching is transitive (if A matches B and B matches C, all three merge) and is done with a
union-find structure, so it stays fast on large exports. Personal domains like Gmail are
never used as a company match, so two different "Ann Lee"s with Gmail addresses stay separate.

When records merge, the most complete one wins, gaps are filled from the others, the highest
engagement counts and most recent activity date are kept, and `source_ids` lists every
original record ID so you can trace the merge back in your CRM.

## Project structure

```
src/crm_toolkit/
  normalize.py          field-level cleaning and title classification
  dedupe.py             duplicate matching and merging
  scoring.py            config-driven lead scoring
  pipeline.py           CSV in → clean CSV out
  report.py             Markdown summary
  cli.py                the crm-clean command
  default_scoring.toml  default scoring rules
tests/                  pytest suite, run by GitHub Actions on every push
data/                   fictional sample HubSpot export (258 rows)
examples/               sample data generator and example output
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

The [CI workflow](.github/workflows/ci.yml) runs the tests on Python 3.11–3.13, then cleans the
sample export and publishes the report to the job summary.

## Roadmap

- [ ] Push cleaned records back to HubSpot through its API
- [ ] Fuzzy name matching (e.g. "Jon" vs "Jonathan")
- [ ] Account-level rollups: score companies, not just contacts

---

*All people and companies in the sample data are fictional and were generated by
[`examples/generate_sample_data.py`](examples/generate_sample_data.py).*
