"""Garmin Connect Personal API client.

The personal key is exchanged for a 24-hour JWT, which is then sent as a bearer token
on data requests (the key itself is not accepted there).
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from typing import Any

import requests

GARMIN_BASE = "https://personal.connectapi.garmin.com"
TOKEN_PATH = "/personalapitoken-service/personal-api/personal-api-key/token"

_token: str | None = None


def garmin_token() -> str:
    global _token
    if _token is None:
        key = os.getenv("GARMIN_API_KEY", "").strip()
        if not key:
            raise RuntimeError("Missing required environment variable: GARMIN_API_KEY")
        response = requests.post(
            GARMIN_BASE + TOKEN_PATH, headers={"Authorization": f"ApiKey {key}", "Accept": "*/*"}, timeout=30
        )
        response.raise_for_status()
        _token = response.text.strip()  # a raw JWT, not JSON
    return _token


def garmin_get(path: str, params: dict[str, Any] | None = None) -> Any:
    response = requests.get(
        GARMIN_BASE + path,
        params=params,
        headers={"Authorization": f"Bearer {garmin_token()}", "Accept": "application/json"},
        timeout=45,
    )
    response.raise_for_status()
    return response.json()


def _windows(start: date, end: date, days: int = 28):
    """Split a date range into windows Garmin accepts (some endpoints cap a request at 28 days)."""
    while start <= end:
        stop = min(start + timedelta(days=days - 1), end)
        yield start, stop
        start = stop + timedelta(days=1)


def fetch_garmin_daily(start: date, end: date) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Per-day recovery metrics from Garmin, keyed by date, plus today's extras for the model.

    Field names follow intervals.icu's wellness rows where both have the metric, so Garmin's
    fresher values can simply replace them.
    """
    days: dict[str, dict[str, Any]] = {}
    hrv_details: dict[str, Any] = {}

    def day(calendar_date: str) -> dict[str, Any]:
        return days.setdefault(calendar_date[:10], {})

    def items(payload: Any) -> list[dict[str, Any]]:
        """Days without data come back as nulls or without a date; skip those."""
        return [i for i in payload or [] if isinstance(i, dict) and isinstance(i.get("calendarDate"), str)]

    def obj(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    failures: list[str] = []

    def guarded(name: str, read) -> None:
        # One endpoint failing (or changing shape) must not cost the others.
        try:
            read()
        except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError) as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")

    for a, b in _windows(start, end):
        a_s, b_s = a.isoformat(), b.isoformat()

        def read_summaries() -> None:
            payload = garmin_get("/usersummary-service/v2/dailysummaries", {"startDate": a_s, "endDate": b_s})
            for item in items(obj(payload).get("data")):
                row = day(item["calendarDate"])
                row["restingHR"] = obj(item.get("heartRate")).get("restingValue")
                row["bodyBattery"] = obj(item.get("bodyBattery")).get("maxValue")
                row["stress"] = obj(item.get("stress")).get("avgLevel")

        def read_sleep() -> None:
            payload = garmin_get("/sleep-service/sleep/dailySleepSummariesByDate", {"startDate": a_s, "endDate": b_s})
            for item in items(payload):
                row = day(item["calendarDate"])
                row["sleepSecs"] = item.get("sleepTimeSeconds")
                row["sleepScore"] = obj(obj(item.get("sleepScores")).get("overall")).get("value")

        def read_hrv() -> None:
            for item in items(obj(garmin_get(f"/hrv-service/hrv/daily/{a_s}/{b_s}")).get("hrvSummaries")):
                day(item["calendarDate"])["hrv"] = item.get("lastNightAvg")
                baseline = obj(item.get("baseline"))
                hrv_details[item["calendarDate"][:10]] = {
                    "status": item.get("status"),
                    "weekly_avg": item.get("weeklyAvg"),
                    "baseline_balanced_range": [baseline.get("balancedLow"), baseline.get("balancedUpper")],
                }

        guarded(f"daily summaries {a_s}", read_summaries)
        guarded(f"sleep {a_s}", read_sleep)
        guarded(f"hrv {a_s}", read_hrv)

    if failures and not days:
        raise RuntimeError("all Garmin requests failed: " + "; ".join(failures[:3]))
    for failure in failures:
        print(f"Garmin partial failure: {failure}", file=sys.stderr)

    extras: dict[str, Any] = {}
    if hrv_details:
        latest = max(hrv_details)
        extras["hrv_status"] = {"date": latest, **hrv_details[latest]}
    try:
        vo2 = garmin_get(f"/metrics-service/metrics/maxmet/daily/{(end - timedelta(days=30)).isoformat()}/{end.isoformat()}")
        values = {}
        for item in vo2 or []:
            for sport in ("generic", "cycling"):
                entry = obj(item).get(sport)
                if isinstance(entry, dict) and entry.get("vo2MaxValue"):
                    values[sport] = {"value": entry["vo2MaxValue"], "date": entry.get("calendarDate")}
        if values:
            extras["vo2max"] = values
    except (requests.RequestException, ValueError, TypeError):
        pass  # VO2max isn't in the published spec; not every account serves it
    # Drop empty values so they don't overwrite intervals.icu data with nothing.
    clean = {d: {k: v for k, v in row.items() if v is not None} for d, row in days.items()}
    return clean, extras
