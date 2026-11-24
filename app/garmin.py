"""Garmin Connect Personal API client.

The personal key is exchanged for a 24-hour JWT, which is then sent as a bearer token
on data requests (the key itself is not accepted there).
"""
from __future__ import annotations

import os
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
