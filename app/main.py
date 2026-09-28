from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import requests
from anthropic import Anthropic

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "config" / "profile.json"
INTERVALS_BASE = "https://intervals.icu/api/v1"


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def intervals_get(path: str, params: dict[str, Any] | None = None) -> Any:
    api_key = require_env("INTERVALS_API_KEY")
    athlete_id = require_env("INTERVALS_ATHLETE_ID")
    url = f"{INTERVALS_BASE}/athlete/{athlete_id}/{path.lstrip('/')}"
    response = requests.get(
        url,
        params=params,
        auth=("API_KEY", api_key),
        timeout=45,
    )
    response.raise_for_status()
    return response.json()


def load_profile() -> dict[str, Any]:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def fetch_training_data() -> dict[str, Any]:
    today = date.today()
    start = today - timedelta(days=28)
    oldest = start.isoformat()
    newest = today.isoformat()

    activities = intervals_get(
        "activities",
        {"oldest": oldest, "newest": newest},
    )
    wellness: list[dict[str, Any]] = []
    try:
        wellness = intervals_get(
            "wellness",
            {"oldest": (today - timedelta(days=14)).isoformat(), "newest": newest},
        )
    except requests.HTTPError as exc:
        # Wellness may be unavailable depending on API permissions/configuration.
        print(f"Wellness endpoint unavailable; continuing without it: {exc}", file=sys.stderr)

    events: list[dict[str, Any]] = []
    try:
        events = intervals_get(
            "events",
            {"oldest": today.isoformat(), "newest": (today + timedelta(days=14)).isoformat()},
        )
    except requests.HTTPError as exc:
        print(f"Events endpoint unavailable; continuing without it: {exc}", file=sys.stderr)

    return {
        "generated_on": today.isoformat(),
        "activities_last_28_days": activities,
        "wellness_last_14_days": wellness,
        "upcoming_events": events,
    }


def compact_data(data: dict[str, Any]) -> dict[str, Any]:
    """Keep the prompt compact while preserving common training and recovery fields."""
    activities = data.get("activities_last_28_days") or []
    wellness = data.get("wellness_last_14_days") or []
    events = data.get("upcoming_events") or []

    activity_fields = (
        "id", "start_date_local", "name", "type", "icu_training_load",
        "icu_intensity", "moving_time", "distance", "average_heartrate",
        "max_heartrate", "average_watts", "icu_ftp", "icu_efficiency",
        "icu_power", "icu_hr_zone_times", "icu_zone_times",
    )
    wellness_fields = (
        "id", "date", "weight", "restingHR", "hrv", "hrvSDNN",
        "sleepSecs", "sleepScore", "readiness", "ctl", "atl", "rampRate",
        "soreness", "fatigue", "stress", "mood",
    )
    event_fields = ("id", "start_date_local", "name", "type", "description")

    def select(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
        return [{k: row[k] for k in fields if k in row} for row in rows if isinstance(row, dict)]

    return {
        "generated_on": data["generated_on"],
        "activities": select(activities, activity_fields),
        "wellness": select(wellness, wellness_fields),
        "upcoming_events": select(events, event_fields),
    }


def generate_report(profile: dict[str, Any], data: dict[str, Any]) -> str:
    client = Anthropic(api_key=require_env("ANTHROPIC_API_KEY"))
    model = os.getenv("ANTHROPIC_MODEL", "").strip() or "claude-sonnet-5"

    system_prompt = (
        "You are a cautious endurance-training planning assistant. Use only the supplied profile and data. "
        "Do not diagnose or invent missing metrics. Clearly state when data is missing. "
        "Give a practical recommendation for today: train/rest, suggested sport and duration/intensity, "
        "why, and what to monitor. Consider recent load, wellness, upcoming events, and the athlete's stated "
        "limits. Do not prescribe intensity above the profile's limits without a clear reason. "
        "If data suggests illness, severe fatigue, unusual symptoms, or a concerning health signal, recommend "
        "rest or professional advice rather than a hard session. Keep the message concise and readable in Telegram."
    )
    user_payload = {
        "athlete_profile": profile,
        "training_data": compact_data(data),
        "output_format": [
            "Today: recommendation",
            "Why: 2-4 concise bullets",
            "Session: optional concrete workout",
            "Caution: what to watch or what data is missing",
        ],
    }
    result = client.messages.create(
        model=model,
        max_tokens=16000,
        system=system_prompt,
        messages=[
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    )
    if result.stop_reason == "refusal":
        raise RuntimeError(f"Claude declined to generate the report: {result.stop_details}")
    text_blocks = [block.text for block in result.content if block.type == "text"]
    return "".join(text_blocks).strip()


def send_telegram(message: str) -> None:
    token = require_env("TELEGRAM_BOT_TOKEN")
    chat_id = require_env("TELEGRAM_CHAT_ID")
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message[:4000], "disable_web_page_preview": True},
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram API returned an error: {body}")


def main() -> None:
    profile = load_profile()
    data = fetch_training_data()
    report = generate_report(profile, data)
    if not report:
        raise RuntimeError("The model returned an empty report.")
    print(report)
    send_telegram(report)


if __name__ == "__main__":
    main()
