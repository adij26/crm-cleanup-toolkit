import pytest

from crm_toolkit import normalize as n


@pytest.mark.parametrize("raw, expected, flag", [
    ("  Maya.Patel@Ledgerline.io ", "maya.patel@ledgerline.io", None),
    ("arjun@gmial.com", "arjun@gmail.com", "fixed_domain_typo"),
    ("info@acme.com", "info@acme.com", "role_based_email"),
    ("sofia@gmail.com", "sofia@gmail.com", "personal_email"),
    ("temp@mailinator.com", "temp@mailinator.com", "disposable_email"),
    ("not-an-email.com", "not-an-email.com", "invalid_email"),
    ("", "", "missing_email"),
])
def test_normalize_email(raw, expected, flag):
    email, flags = n.normalize_email(raw)
    assert email == expected
    if flag:
        assert flag in flags
    else:
        assert flags == []


@pytest.mark.parametrize("raw, expected", [
    ("  jOHN   smith ", "John Smith"),
    ("o'brien", "O'Brien"),
    ("MCALLISTER", "McAllister"),
    ("mary-jane", "Mary-Jane"),
])
def test_normalize_name(raw, expected):
    assert n.normalize_name(raw) == expected


@pytest.mark.parametrize("raw, expected, ok", [
    ("(415) 555-0134", "+14155550134", True),
    ("415.555.0134", "+14155550134", True),
    ("1 415 555 0134", "+14155550134", True),
    ("415-555-0134 ext. 12", "+14155550134", True),
    ("+44 20 7946 0958", "+442079460958", True),
    ("n/a", "n/a", False),
])
def test_normalize_phone(raw, expected, ok):
    phone, flags = n.normalize_phone(raw)
    assert phone == expected
    assert (flags == []) == ok


@pytest.mark.parametrize("raw, expected", [
    ("Acme, Inc.", "Acme"),
    ("ACME CORP", "Acme"),
    ("Northwind Capital LLC", "Northwind Capital"),
    ("brightpath logistics co.", "Brightpath Logistics"),
])
def test_normalize_company(raw, expected):
    assert n.normalize_company(raw) == expected


@pytest.mark.parametrize("title, seniority, function", [
    ("Chief Financial Officer", "C-Level", "Finance"),
    ("VP of Finance", "VP", "Finance"),
    ("Director of FP&A", "Director", "Finance"),
    ("Accounts Payable Manager", "Manager", "Finance"),
    ("Head of Revenue Operations", "Director", "Operations"),
    ("Content Marketing Specialist", "Individual Contributor", "Marketing"),
    ("Finance Intern", "Entry", "Finance"),
    ("Founder & CEO", "C-Level", "Executive"),
])
def test_classify_title(title, seniority, function):
    clean = n.normalize_title(title)
    assert n.classify_seniority(clean) == seniority
    assert n.classify_function(clean) == function


def test_normalize_title_expands_abbreviations():
    assert n.normalize_title("sr. accountant") == "Senior Accountant"
    assert n.normalize_title("vp finance") == "VP Finance"


@pytest.mark.parametrize("raw, expected", [
    ("marketing qualified lead", "MQL"), ("sql", "SQL"), ("lead", "Lead"), ("Evangelist", "Evangelist"),
])
def test_normalize_stage(raw, expected):
    assert n.normalize_stage(raw) == expected
