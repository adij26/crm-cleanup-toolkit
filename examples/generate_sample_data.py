"""Generate a realistic, deliberately messy CRM export for demos and tests.

All people and companies are fictional. The script is seeded, so it produces
the same file every time:  python examples/generate_sample_data.py
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(26)

FIRST = ["Maya", "Arjun", "Sofia", "Liam", "Priya", "Noah", "Elena", "Marcus", "Aisha", "Daniel",
         "Hana", "Lucas", "Zara", "Ethan", "Leila", "Omar", "Grace", "Ravi", "Chloe", "Mateo",
         "Nina", "Kai", "Isabel", "Theo", "Ananya", "Owen", "Mei", "Jonah", "Fatima", "Sean"]
LAST = ["Patel", "Nguyen", "Garcia", "O'Brien", "Kim", "Shah", "McAllister", "Rossi", "Chen",
        "Okafor", "Silva", "Kowalski", "Haddad", "Iyer", "Brennan", "Larsen", "Mendez", "Tanaka",
        "Fischer", "Reyes", "Andersson", "Moreau", "Sato", "Kapoor", "Walsh"]
COMPANIES = [
    ("Ledgerline", "ledgerline.io", 140), ("Northwind Capital", "northwindcap.com", 820),
    ("Brightpath Logistics", "brightpath.co", 2400), ("Cobalt Health", "cobalthealth.com", 650),
    ("Tandem Retail", "tandemretail.com", 45), ("Fernleaf Foods", "fernleaf.com", 310),
    ("Quanta Robotics", "quantarobotics.ai", 95), ("Harborview Hotels", "harborview.com", 1300),
    ("Pinecrest Software", "pinecrest.dev", 220), ("Summit Freight", "summitfreight.com", 75),
    ("Mosaic Media", "mosaicmedia.co", 30), ("Orbital Energy", "orbitalenergy.com", 5100),
    ("Kestrel Bio", "kestrelbio.com", 180), ("Lumen Payments", "lumenpay.com", 410),
    ("Driftwood Studios", "driftwood.studio", 8),
]
SUFFIXES = ["", " Inc.", ", Inc", " LLC", " Corp", " Co."]
TITLES = [
    "Chief Financial Officer", "CFO", "VP of Finance", "vp finance", "Director of FP&A",
    "Controller", "Sr. Accountant", "AP Specialist", "Accounts Payable Manager",
    "Head of Revenue Operations", "Revops Manager", "Director of Operations", "COO",
    "Marketing Manager", "Content Marketing Specialist", "VP Marketing", "Sales Development Rep",
    "Account Executive", "Software Engineer", "IT Director", "Founder & CEO", "Finance Intern",
    "Treasury Analyst", "Senior Financial Analyst", "Office Manager",
]
SOURCES = ["Organic Search", "Paid Social", "Webinar", "Event", "Referral", "Direct Traffic", "Email"]
STAGES = ["lead", "Lead", "MQL", "marketing qualified lead", "SQL", "Opportunity", "subscriber"]
TODAY = date(2026, 11, 15)


def phone_variant() -> str:
    a, b, c = random.randint(200, 989), random.randint(200, 999), random.randint(1000, 9999)
    return random.choice([
        f"({a}) {b}-{c}", f"{a}-{b}-{c}", f"{a}.{b}.{c}", f"+1 {a} {b} {c}",
        f"1{a}{b}{c}", f"{a}{b}{c} ext. 12", "n/a", "",
    ])


def messy_case(s: str) -> str:
    return random.choice([s, s.lower(), s.upper(), f"  {s} "])


def make_person(i: int) -> dict:
    first, last = random.choice(FIRST), random.choice(LAST)
    company, domain, size = random.choice(COMPANIES)
    local = random.choice([f"{first}.{last}", f"{first[0]}{last}", first]).lower().replace("'", "")
    email = f"{local}@{domain}"
    roll = random.random()
    if roll < 0.06:
        email = f"{local}@gmail.com"
    elif roll < 0.09:
        email = f"{random.choice(['info', 'sales', 'hello'])}@{domain}"
    elif roll < 0.11:
        email = f"{local}@gmial.com"
    elif roll < 0.13:
        email = f"{local}.{domain}"  # missing @
    elif roll < 0.14:
        email = f"{local}@mailinator.com"
    return {
        "Record ID": str(100000 + i),
        "First Name": messy_case(first),
        "Last Name": messy_case(last),
        "Email": random.choice([email, email.upper(), f" {email}"]),
        "Phone Number": phone_variant(),
        "Company Name": company + random.choice(SUFFIXES),
        "Job Title": random.choice(TITLES),
        "Number of Employees": f"{size:,}" if random.random() < 0.3 else str(size),
        "Country/Region": random.choice(["United States", "United States", "USA", "Canada", "United Kingdom"]),
        "Lifecycle Stage": random.choice(STAGES),
        "Original Source": random.choice(SOURCES),
        "Marketing emails opened": str(random.choice([0, 0, 1, 2, 3, 5, 8, 12, 20])),
        "Number of Pageviews": str(random.choice([0, 1, 2, 4, 7, 11, 18, 30])),
        "Last Activity Date": (TODAY - timedelta(days=random.choice([1, 3, 9, 20, 45, 80, 150, 400]))).isoformat(),
        "Contact owner": random.choice(["Jordan Lee", "Sam Rivera", ""]),
    }


def make_duplicate(person: dict, i: int) -> dict:
    """Same human, entered again from another form or list upload."""
    dup = dict(person)
    dup["Record ID"] = str(100000 + i)
    dup["First Name"] = person["First Name"].strip().lower()
    dup["Company Name"] = person["Company Name"].split(",")[0].split(" Inc")[0].upper()
    dup["Email"] = person["Email"].strip().upper()
    dup["Phone Number"] = random.choice(["", phone_variant()])
    dup["Job Title"] = random.choice([person["Job Title"], ""])
    dup["Marketing emails opened"] = str(random.randint(0, 25))
    dup["Last Activity Date"] = (TODAY - timedelta(days=random.randint(0, 60))).isoformat()
    return dup


def main() -> None:
    rows, people = [], []
    for i in range(220):
        p = make_person(i)
        people.append(p)
        rows.append(p)
    for j, p in enumerate(random.sample(people, 38)):
        rows.append(make_duplicate(p, 1000 + j))
    random.shuffle(rows)

    out = Path(__file__).resolve().parent.parent / "data" / "sample_hubspot_export.csv"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
