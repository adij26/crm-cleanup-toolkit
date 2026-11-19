import csv
from datetime import date

from crm_toolkit.dedupe import dedupe
from crm_toolkit.pipeline import map_columns, run
from crm_toolkit.report import render_markdown
from crm_toolkit.scoring import load_config, score_lead

TODAY = date(2026, 11, 15)


def rec(**kw):
    base = {"record_id": "", "first_name": "", "last_name": "", "email": "", "company": "",
            "email_opens": "0", "last_activity_date": "", "flags": []}
    base.update(kw)
    return base


def test_dedupe_on_email():
    rows = [rec(record_id="1", email="a@x.com", first_name="Ann", email_opens="3"),
            rec(record_id="2", email="a@x.com", company="X", email_opens="9")]
    unique, removed = dedupe(rows)
    assert removed == 1
    merged = unique[0]
    assert merged["company"] == "X"          # filled from the other record
    assert merged["email_opens"] == "9"      # highest engagement kept
    assert merged["merged_count"] == 2
    assert "merged_duplicates" in merged["flags"]


def test_dedupe_on_name_and_company():
    rows = [rec(record_id="1", first_name="Ann", last_name="Lee", company="Acme", email="ann@acme.com"),
            rec(record_id="2", first_name="Ann", last_name="Lee", company="ACME", email="")]
    unique, removed = dedupe(rows)
    assert removed == 1


def test_dedupe_is_transitive():
    # 1 and 2 share an email, 2 and 3 share name+company -> all one person
    rows = [rec(record_id="1", email="ann@acme.com"),
            rec(record_id="2", email="ann@acme.com", first_name="Ann", last_name="Lee", company="Acme"),
            rec(record_id="3", first_name="Ann", last_name="Lee", company="Acme")]
    unique, removed = dedupe(rows)
    assert len(unique) == 1 and removed == 2


def test_different_people_stay_separate():
    rows = [rec(first_name="Ann", last_name="Lee", email="ann@gmail.com"),
            rec(first_name="Ann", last_name="Lee", email="annlee@gmail.com")]
    unique, _ = dedupe(rows)
    assert len(unique) == 2  # same name, free email domain, no company -> not merged


def test_score_rewards_finance_leaders():
    config = load_config()
    cfo = {"seniority": "C-Level", "function": "Finance", "company_size": "400",
           "email_opens": "6", "page_views": "10", "last_activity_date": "2026-11-10", "flags": []}
    intern = {"seniority": "Entry", "function": "Marketing", "company_size": "5",
              "email_opens": "0", "page_views": "0", "last_activity_date": "2025-01-01",
              "flags": ["personal_email"]}
    cfo_score, cfo_grade, reasons = score_lead(cfo, config, today=TODAY)
    intern_score, intern_grade, _ = score_lead(intern, config, today=TODAY)
    assert cfo_grade == "A" and cfo_score > intern_score
    assert intern_grade == "D"
    assert any("seniority" in r for r in reasons)


def test_score_is_clamped():
    config = load_config()
    bad = {"seniority": "Unknown", "function": "Other", "flags": ["invalid_email", "disposable_email"]}
    score, grade, _ = score_lead(bad, config, today=TODAY)
    assert score == 0 and grade == "D"


def test_map_columns_handles_export_headers():
    mapping = map_columns(["First Name", "E-mail", "Company Name", "Number of Employees", "Favourite Color"])
    assert mapping == {"first_name": "First Name", "email": "E-mail",
                       "company": "Company Name", "company_size": "Number of Employees"}


def test_full_pipeline(tmp_path):
    src = tmp_path / "in.csv"
    with open(src, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Name", "Email", "Company", "Title", "Employees", "Last Activity Date"])
        w.writerow(["maya patel", "Maya@Ledgerline.io", "Ledgerline Inc.", "CFO", "140", "2026-11-12"])
        w.writerow(["MAYA PATEL", "maya@ledgerline.io ", "LEDGERLINE", "", "", "2026-10-01"])
        w.writerow(["Theo Kim", "info@pinecrest.dev", "Pinecrest", "Marketing Manager", "220", ""])
    out = tmp_path / "out.csv"
    summary = run(src, out, today=TODAY)

    assert summary.rows_in == 3 and summary.rows_out == 2 and summary.duplicates_removed == 1
    rows = list(csv.DictReader(open(out)))
    assert rows[0]["first_name"] == "Maya" and rows[0]["company"] == "Ledgerline"
    assert rows[0]["lead_grade"] in {"A", "B"}
    assert "role_based_email" in rows[1]["flags"]

    report = render_markdown(summary)
    assert "Duplicates merged | 1" in report


def test_merge_drops_stale_field_flags():
    rows = [rec(record_id="1", email="a@x.com", phone="n/a", flags=["invalid_phone"]),
            rec(record_id="2", email="a@x.com", phone="+14155550134")]
    merged = dedupe(rows)[0][0]
    assert merged["phone"] == "+14155550134"
    assert "invalid_phone" not in merged["flags"]
