"""One-off: print the SHAPE (keys and types, never values) of Garmin responses, to write parsers."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import requests

from app.garmin import garmin_get


def shape(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return "..."
    if isinstance(value, dict):
        return {k: shape(v, depth + 1) for k, v in list(value.items())[:60]}
    if isinstance(value, list):
        return [f"list[{len(value)}]", shape(value[0], depth + 1)] if value else "list[0]"
    return type(value).__name__


def main() -> None:
    today = date.today()
    start = (today - timedelta(days=3)).isoformat()
    end = today.isoformat()
    probes = [
        ("/usersummary-service/v2/dailysummaries", {"startDate": start, "endDate": end}),
        ("/sleep-service/sleep/dailySleepSummariesByDate", {"startDate": start, "endDate": end}),
        (f"/hrv-service/hrv/daily/{start}/{end}", None),
        ("/wellness-service/wellness/bodyBattery/reports/daily", {"startDate": start, "endDate": end}),
        (f"/usersummary-service/stats/stress/daily/{start}/{end}", None),
        (f"/metrics-service/metrics/maxmet/daily/{start}/{end}", None),
    ]
    for path, params in probes:
        try:
            print(path, "->", shape(garmin_get(path, params)))
        except requests.HTTPError as exc:
            print(path, "-> HTTP", exc.response.status_code if exc.response is not None else "?")


if __name__ == "__main__":
    main()
