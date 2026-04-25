from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


_LANGUAGE_PROFILE_PATH = Path(__file__).resolve().parent.parent / "config" / "language_profiles.json"


@lru_cache(maxsize=1)
def _load_profiles() -> dict[str, dict]:
    payload = json.loads(_LANGUAGE_PROFILE_PATH.read_text(encoding="utf-8"))
    languages = payload.get("languages", [])
    return {
        str(language["language_code"]).lower(): dict(language)
        for language in languages
        if language.get("language_code")
    }


def load_language_profile(language_code: str) -> dict:
    code = str(language_code or "").lower()
    profiles = _load_profiles()
    if code not in profiles:
        raise ValueError(f"Unsupported language_code={language_code}")
    return dict(profiles[code])


def get_language_inheritance_chain(language_code: str) -> list[str]:
    profile = load_language_profile(language_code)
    chain = [str(language_code).lower()]
    chain.extend(str(item).lower() for item in profile.get("inherits_from", []))
    return list(dict.fromkeys(chain))


def get_language_error_taxonomy(language_code: str) -> list[str]:
    profile = load_language_profile(language_code)
    return [str(item) for item in profile.get("error_taxonomy", [])]


def get_normalization_rules(language_code: str) -> list[str]:
    profile = load_language_profile(language_code)
    return [str(item) for item in profile.get("normalization_rules", [])]


def get_adapter_status(language_code: str) -> str:
    profile = load_language_profile(language_code)
    return str(profile.get("adapter_status") or "not_ready")


def is_adapter_available(language_code: str) -> bool:
    return get_adapter_status(language_code) in {"experimental", "ready", "production", "base"}
