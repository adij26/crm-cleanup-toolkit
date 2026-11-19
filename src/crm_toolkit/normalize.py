"""Field-level cleanup: emails, names, phones, companies and job titles.

Every function here is pure (input in, cleaned value out) so it is easy to
test and safe to run on any CRM export.
"""

from __future__ import annotations

import re

EMAIL_RE = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$")

# Addresses that belong to a team inbox rather than a person.
ROLE_PREFIXES = {
    "info", "sales", "support", "admin", "hello", "contact", "marketing",
    "team", "office", "billing", "noreply", "no-reply", "help", "careers",
}

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "aol.com", "proton.me", "protonmail.com", "live.com", "me.com",
}

DISPOSABLE_DOMAINS = {
    "mailinator.com", "10minutemail.com", "guerrillamail.com",
    "tempmail.com", "trashmail.com", "yopmail.com",
}

# Common typos people make in the domain part of an email.
DOMAIN_TYPOS = {
    "gmial.com": "gmail.com",
    "gmai.com": "gmail.com",
    "gamil.com": "gmail.com",
    "gmail.co": "gmail.com",
    "yahooo.com": "yahoo.com",
    "hotmial.com": "hotmail.com",
    "outlok.com": "outlook.com",
}

COMPANY_SUFFIXES = re.compile(
    r"[,.]?\s+(inc|inc\.|incorporated|llc|l\.l\.c\.|ltd|ltd\.|limited|corp|corp\.|"
    r"corporation|co|co\.|company|gmbh|plc|pbc)\.?$",
    re.IGNORECASE,
)

# Order matters: the first match wins, so put the most senior patterns first.
SENIORITY_RULES = [
    ("C-Level", r"\b(chief|ceo|cfo|coo|cto|cmo|cro|cio|founder|co-founder|owner|president)\b"),
    ("VP", r"\b(vp|vice president|svp|evp)\b"),
    ("Director", r"\b(director|head of)\b"),
    ("Manager", r"\b(manager|mgr|lead|supervisor|controller)\b"),
    ("Individual Contributor", r"\b(analyst|specialist|associate|coordinator|accountant|"
                               r"engineer|representative|rep|executive|consultant)\b"),
    ("Entry", r"\b(intern|assistant|junior|jr)\b"),
]

FUNCTION_RULES = [
    ("Finance", r"\b(finance|financial|cfo|controller|accounting|accountant|fp&a|treasury|"
                r"ap|ar|payable|receivable|tax|audit)\b"),
    ("Operations", r"\b(operations|ops|coo|revops|revenue operations|procurement|supply)\b"),
    ("Marketing", r"\b(marketing|cmo|brand|growth|demand gen|content|seo)\b"),
    ("Sales", r"\b(sales|cro|account executive|business development|bdr|sdr)\b"),
    ("Technology", r"\b(cto|cio|engineer|engineering|it|developer|data|technology)\b"),
    ("Executive", r"\b(ceo|founder|co-founder|owner|president)\b"),
]

TITLE_ABBREVIATIONS = {
    r"\bsr\b\.?": "Senior",
    r"\bjr\b\.?": "Junior",
    r"\bmgr\b\.?": "Manager",
    r"\bdir\b\.?": "Director",
    r"\bvp\b": "VP",
    r"\bfp&a\b": "FP&A",
}


def clean_whitespace(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def normalize_email(raw: str | None) -> tuple[str, list[str]]:
    """Return (cleaned_email, flags). Flags explain anything worth a human look."""
    flags: list[str] = []
    email = clean_whitespace(raw).lower().strip("<>\"' ")
    email = email.replace("mailto:", "")
    if not email:
        return "", ["missing_email"]

    if "@" in email:
        local, _, domain = email.rpartition("@")
        if domain in DOMAIN_TYPOS:
            domain = DOMAIN_TYPOS[domain]
            flags.append("fixed_domain_typo")
        email = f"{local}@{domain}"

    if not EMAIL_RE.match(email):
        return email, flags + ["invalid_email"]

    local, domain = email.split("@")
    if local.split("+")[0] in ROLE_PREFIXES:
        flags.append("role_based_email")
    if domain in FREE_EMAIL_DOMAINS:
        flags.append("personal_email")
    if domain in DISPOSABLE_DOMAINS:
        flags.append("disposable_email")
    return email, flags


def email_domain(email: str) -> str:
    return email.split("@", 1)[1] if "@" in email else ""


def normalize_name(raw: str | None) -> str:
    """'  jOHN   mcdonald ' -> 'John McDonald'; keeps O'Brien and hyphenated names."""
    name = clean_whitespace(raw)
    if not name:
        return ""

    def fix(word: str) -> str:
        word = word.lower()
        parts = re.split(r"([\-'])", word)
        out = "".join(p.capitalize() if p not in "-'" else p for p in parts)
        if out.startswith("Mc") and len(out) > 2:
            out = "Mc" + out[2].upper() + out[3:]
        return out

    return " ".join(fix(w) for w in name.split(" "))


def normalize_phone(raw: str | None, default_country: str = "1") -> tuple[str, list[str]]:
    """Normalize to +<country><number>. US/CA numbers are assumed when no country code."""
    text = clean_whitespace(raw)
    if not text:
        return "", []
    text = re.split(r"\s*(?:x|ext\.?|extension)\s*\d+$", text, flags=re.IGNORECASE)[0]
    digits = re.sub(r"\D", "", text)
    if text.startswith("+"):
        return ("+" + digits, []) if 8 <= len(digits) <= 15 else (text, ["invalid_phone"])
    if len(digits) == 10:
        return f"+{default_country}{digits}", []
    if len(digits) == 11 and digits.startswith(default_country):
        return f"+{digits}", []
    return text, ["invalid_phone"]


def normalize_company(raw: str | None) -> str:
    """Strip legal suffixes and fix casing so 'ACME, Inc.' and 'Acme' match."""
    name = clean_whitespace(raw)
    if not name:
        return ""
    previous = None
    while previous != name:
        previous = name
        name = COMPANY_SUFFIXES.sub("", name).strip(" ,.")
    if name.isupper() and len(name) > 3:
        name = name.title()
    elif name.islower():
        name = name.title()
    return name


def company_key(name: str) -> str:
    """Loose matching key: lowercase letters and digits only."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def normalize_title(raw: str | None) -> str:
    title = clean_whitespace(raw)
    if not title:
        return ""
    for pattern, replacement in TITLE_ABBREVIATIONS.items():
        title = re.sub(pattern, replacement, title, flags=re.IGNORECASE)
    small = {"of", "and", "the", "for", "&"}
    words = []
    for i, word in enumerate(title.split(" ")):
        if word.isupper() and len(word) <= 5:  # keep acronyms like CFO, AP, FP&A
            words.append(word)
        elif i > 0 and word.lower() in small:
            words.append(word.lower())
        else:
            words.append(word[:1].upper() + word[1:].lower())
    return " ".join(words)


def _first_match(rules: list[tuple[str, str]], text: str, default: str) -> str:
    lowered = text.lower()
    for label, pattern in rules:
        if re.search(pattern, lowered):
            return label
    return default


def classify_seniority(title: str) -> str:
    return _first_match(SENIORITY_RULES, title, "Unknown")


def classify_function(title: str) -> str:
    return _first_match(FUNCTION_RULES, title, "Other")


LIFECYCLE_STAGES = {
    "subscriber": "Subscriber",
    "lead": "Lead",
    "mql": "MQL",
    "marketing qualified lead": "MQL",
    "sql": "SQL",
    "sales qualified lead": "SQL",
    "opportunity": "Opportunity",
    "customer": "Customer",
}


def normalize_stage(raw: str | None) -> str:
    stage = clean_whitespace(raw)
    return LIFECYCLE_STAGES.get(stage.lower(), stage.title())
