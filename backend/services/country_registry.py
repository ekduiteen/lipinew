from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional


_COUNTRY_PROFILE_PATH = Path(__file__).resolve().parent.parent / "config" / "country_profiles.json"


@lru_cache(maxsize=1)
def _load_profiles() -> dict[str, dict]:
    payload = json.loads(_COUNTRY_PROFILE_PATH.read_text(encoding="utf-8"))
    countries = payload.get("countries", [])
    return {
        str(country["country_code"]).upper(): dict(country)
        for country in countries
        if country.get("country_code")
    }


def load_country_profile(country_code: str) -> dict:
    code = str(country_code or "").upper()
    profiles = _load_profiles()
    if code not in profiles:
        raise ValueError(f"Unsupported country_code={country_code}")
    return dict(profiles[code])


def get_base_asr_languages(country_code: str, region: Optional[str] = None) -> list[str]:
    profile = load_country_profile(country_code)
    if region:
        regional = (profile.get("regional_base_language_options") or {}).get(region)
        if regional:
            return [str(lang) for lang in regional]
    return [str(lang) for lang in profile.get("base_asr_languages", [])]


def validate_country_target_language(country_code: str, target_language: str) -> bool:
    profile = load_country_profile(country_code)
    supported = {str(code).lower() for code in profile.get("supported_target_languages", [])}
    return str(target_language or "").lower() in supported
