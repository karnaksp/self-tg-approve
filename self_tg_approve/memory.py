"""Small in-memory conversation helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import MutableMapping, TypedDict


class ChatMessage(TypedDict):
    role: str
    content: str


def session_expired(
    last_activity: object,
    now: datetime,
    ttl_minutes: int,
) -> bool:
    if not isinstance(last_activity, datetime):
        return bool(last_activity)
    return now - last_activity >= timedelta(minutes=ttl_minutes)


def clear_expired_history(
    state: MutableMapping[str, object],
    now: datetime,
    ttl_minutes: int,
) -> bool:
    """Erase stale Mistral context while leaving unrelated bot state untouched."""
    last_activity = state.get("last_activity")
    if not last_activity or not session_expired(last_activity, now, ttl_minutes):
        return False
    state["mistral_history"] = []
    state.pop("last_activity", None)
    state["session_expired_notice"] = True
    return True


def trim_history(
    history: list[ChatMessage],
    *,
    max_messages: int,
    max_chars: int,
) -> list[ChatMessage]:
    """Keep recent complete user/assistant pairs inside both limits."""
    recent = history[-max_messages:]
    while recent and sum(len(item["content"]) for item in recent) > max_chars:
        recent = recent[2:] if len(recent) >= 2 else []
    if recent and recent[0]["role"] == "assistant":
        recent = recent[1:]
    return recent


def append_exchange(
    history: list[ChatMessage],
    user_text: str,
    assistant_text: str,
    *,
    max_messages: int,
    max_chars: int,
) -> list[ChatMessage]:
    updated = [
        *history,
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": assistant_text},
    ]
    return trim_history(
        updated,
        max_messages=max_messages,
        max_chars=max_chars,
    )


def split_telegram_text(text: str, limit: int = 4_000) -> list[str]:
    """Split plain text without relying on Telegram Markdown parsing."""
    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit + 1)
        if split_at < limit // 2:
            split_at = text.rfind(" ", 0, limit + 1)
        if split_at <= 0:
            split_at = limit
        chunks.append(text[:split_at].rstrip())
        text = text[split_at:].lstrip()
    if text:
        chunks.append(text)
    return chunks
