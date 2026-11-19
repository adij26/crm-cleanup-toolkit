"""Rule-based lead scoring driven by a TOML config file.

The score is deliberately transparent: every point is explained in the
`score_reasons` column so a sales or marketing team can see *why* a lead is
an A and argue with the weights, rather than trusting a black box.
"""

from __future__ import annotations

import tomllib
from datetime import date
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).with_name("default_scoring.toml")


def load_config(path: str | Path | None = None) -> dict:
    with open(path or DEFAULT_CONFIG, "rb") as fh:
        return tomllib.load(fh)


def _num(value) -> float:
    try:
        return float(str(value).replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def _size_points(size: float, bands: list[list[float]]) -> float:
    for low, high, points in bands:
        if low <= size <= high:
            return points
    return 0


def _recency_points(last_activity: str, rules: list[list[float]], today: date) -> tuple[float, int | None]:
    try:
        days = (today - date.fromisoformat(str(last_activity)[:10])).days
    except ValueError:
        return 0, None
    for max_days, points in rules:
        if days <= max_days:
            return points, days
    return 0, days


def score_lead(record: dict, config: dict, today: date | None = None) -> tuple[int, str, list[str]]:
    """Return (score 0-100, grade, reasons)."""
    today = today or date.today()
    weights = config["weights"]
    reasons: list[str] = []
    total = 0.0

    def add(points: float, why: str) -> None:
        nonlocal total
        if points:
            total += points
            reasons.append(f"{points:+g} {why}")

    seniority = record.get("seniority", "Unknown")
    add(weights["seniority"].get(seniority, 0), f"seniority: {seniority}")

    function = record.get("function", "Other")
    add(weights["function"].get(function, 0), f"function: {function}")

    size = _num(record.get("company_size"))
    if size:
        add(_size_points(size, config["company_size"]["bands"]), f"company size: {int(size)}")

    eng = config["engagement"]
    opens = _num(record.get("email_opens"))
    add(min(opens * eng["points_per_email_open"], eng["max_email_points"]), f"email opens: {int(opens)}")
    views = _num(record.get("page_views"))
    add(min(views * eng["points_per_page_view"], eng["max_page_view_points"]), f"page views: {int(views)}")

    pts, days = _recency_points(record.get("last_activity_date", ""), eng["recency"], today)
    if days is not None:
        add(pts, f"last active {days} day{'' if days == 1 else 's'} ago")

    for flag in record.get("flags", []):
        add(config["penalties"].get(flag, 0), f"flag: {flag}")

    score = int(round(max(0, min(100, total))))
    grade = "D"
    for letter, threshold in sorted(config["grades"].items(), key=lambda kv: -kv[1]):
        if score >= threshold:
            grade = letter
            break
    return score, grade, reasons
