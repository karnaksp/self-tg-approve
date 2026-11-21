"""Environment-backed configuration with strict startup validation."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping


class ConfigError(ValueError):
    """Raised when required configuration is absent or invalid."""


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise ConfigError(f"Не задана обязательная переменная {name}")
    return value


def _integer(
    env: Mapping[str, str],
    name: str,
    default: int | None = None,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    raw = env.get(name)
    if raw is None or not raw.strip():
        if default is None:
            raise ConfigError(f"Не задана обязательная переменная {name}")
        value = default
    else:
        try:
            value = int(raw)
        except ValueError as exc:
            raise ConfigError(f"{name} должна быть целым числом") from exc

    if minimum is not None and value < minimum:
        raise ConfigError(f"{name} должна быть не меньше {minimum}")
    if maximum is not None and value > maximum:
        raise ConfigError(f"{name} должна быть не больше {maximum}")
    return value


def _floating(
    env: Mapping[str, str],
    name: str,
    default: float,
    *,
    minimum: float,
    maximum: float,
) -> float:
    raw = env.get(name)
    try:
        value = default if raw is None or not raw.strip() else float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} должна быть числом") from exc
    if not minimum <= value <= maximum:
        raise ConfigError(f"{name} должна быть от {minimum} до {maximum}")
    return value


def _chat_id(value: str) -> int | str:
    value = value.strip()
    if value.lstrip("-").isdigit():
        return int(value)
    if value.startswith("@") and len(value) > 1:
        return value
    raise ConfigError("CHANNEL_ID должен быть числовым ID или @username канала")


def _user_ids(env: Mapping[str, str], name: str) -> frozenset[int]:
    raw = env.get(name, "").strip()
    if not raw:
        return frozenset()
    try:
        return frozenset(int(item.strip()) for item in raw.split(",") if item.strip())
    except ValueError as exc:
        raise ConfigError(f"{name} должен содержать числовые ID через запятую") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings. Secret fields are excluded from representations."""

    telegram_token: str = field(repr=False)
    channel_id: int | str
    admin_id: int
    mistral_api_key: str = field(repr=False)
    mistral_model: str = "mistral-small-latest"
    mistral_api_url: str = "https://api.mistral.ai/v1/chat/completions"
    mistral_timeout_seconds: float = 45.0
    mistral_max_tokens: int = 600
    mistral_temperature: float = 0.45
    session_ttl_minutes: int = 60
    session_history_messages: int = 12
    session_history_chars: int = 12_000
    request_cooldown_seconds: float = 3.0
    mistral_allowed_user_ids: frozenset[int] = frozenset()
    invite_link_ttl_hours: int = 24
    log_level: str = "INFO"
    llm_proxy: str | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        source = os.environ if env is None else env
        raw_api_key = (
            source.get("GEMINI_API_KEY", "").strip()
            or source.get("MISTRAL_API_KEY", "").strip()
        )
        if not raw_api_key:
            raise ConfigError("Не задана обязательная переменная MISTRAL_API_KEY")

        is_gemini = bool(source.get("GEMINI_API_KEY")) or raw_api_key.startswith(("AQ.", "AIza"))
        model = source.get("GEMINI_MODEL") or source.get("MISTRAL_MODEL", "").strip()
        if not model or (is_gemini and model == "mistral-small-latest"):
            model = "gemini-3.1-flash-lite" if is_gemini else "mistral-small-latest"

        default_url = (
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            if is_gemini
            else "https://api.mistral.ai/v1/chat/completions"
        )
        api_url = (
            source.get("GEMINI_API_URL")
            or source.get("MISTRAL_API_URL")
            or source.get("LLM_API_URL")
            or default_url
        )

        log_level = source.get("LOG_LEVEL", "INFO").strip().upper()
        if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ConfigError("LOG_LEVEL имеет недопустимое значение")

        llm_proxy = (
            source.get("LLM_PROXY", "").strip()
            or source.get("HTTPS_PROXY", "").strip()
            or source.get("HTTP_PROXY", "").strip()
            or None
        )

        telegram_token = _required(source, "TOKEN")
        admin_id = _integer(source, "ADMIN_ID")
        bot_id_part = telegram_token.split(":", 1)[0]
        if bot_id_part.isdigit() and int(bot_id_part) == admin_id:
            raise ConfigError(
                "ADMIN_ID не может совпадать с ID самого бота (из TOKEN). "
                "В ADMIN_ID должен быть указан ваш личный Telegram ID (узнать его можно у @userinfobot)."
            )

        return cls(
            telegram_token=telegram_token,
            channel_id=_chat_id(_required(source, "CHANNEL_ID")),
            admin_id=admin_id,
            mistral_api_key=raw_api_key,
            mistral_model=model,
            mistral_api_url=api_url,
            mistral_timeout_seconds=_floating(
                source,
                "MISTRAL_TIMEOUT_SECONDS",
                45.0,
                minimum=5.0,
                maximum=120.0,
            ),
            mistral_max_tokens=_integer(
                source,
                "MISTRAL_MAX_TOKENS",
                600,
                minimum=64,
                maximum=2_048,
            ),
            mistral_temperature=_floating(
                source,
                "MISTRAL_TEMPERATURE",
                0.45,
                minimum=0.0,
                maximum=1.0,
            ),
            session_ttl_minutes=_integer(
                source,
                "SESSION_TTL_MINUTES",
                60,
                minimum=5,
                maximum=1_440,
            ),
            session_history_messages=_integer(
                source,
                "SESSION_HISTORY_MESSAGES",
                12,
                minimum=2,
                maximum=40,
            ),
            session_history_chars=_integer(
                source,
                "SESSION_HISTORY_CHARS",
                12_000,
                minimum=1_000,
                maximum=50_000,
            ),
            request_cooldown_seconds=_floating(
                source,
                "MISTRAL_REQUEST_COOLDOWN_SECONDS",
                3.0,
                minimum=0.0,
                maximum=60.0,
            ),
            mistral_allowed_user_ids=_user_ids(source, "MISTRAL_ALLOWED_USER_IDS"),
            invite_link_ttl_hours=_integer(
                source,
                "INVITE_LINK_TTL_HOURS",
                24,
                minimum=1,
                maximum=168,
            ),
            log_level=log_level,
            llm_proxy=llm_proxy,
        )
