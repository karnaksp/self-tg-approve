from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from self_tg_approve.memory import (
    append_exchange,
    clear_expired_history,
    session_expired,
    split_telegram_text,
    trim_history,
)


class MemoryTests(unittest.TestCase):
    def test_session_ttl(self) -> None:
        now = datetime.now(UTC)
        self.assertFalse(session_expired(now - timedelta(minutes=59), now, 60))
        self.assertTrue(session_expired(now - timedelta(minutes=60), now, 60))
        self.assertFalse(session_expired(None, now, 60))

    def test_expired_history_is_actually_erased(self) -> None:
        now = datetime.now(UTC)
        state: dict[str, object] = {
            "last_activity": now - timedelta(minutes=61),
            "mistral_history": [{"role": "user", "content": "secret context"}],
            "awaiting_photo": True,
        }

        self.assertTrue(clear_expired_history(state, now, 60))
        self.assertEqual(state["mistral_history"], [])
        self.assertNotIn("last_activity", state)
        self.assertTrue(state["session_expired_notice"])
        self.assertTrue(state["awaiting_photo"])

    def test_history_keeps_recent_complete_pairs(self) -> None:
        history = []
        for number in range(5):
            history = append_exchange(
                history,
                f"user-{number}",
                f"assistant-{number}",
                max_messages=4,
                max_chars=1_000,
            )

        self.assertEqual(len(history), 4)
        self.assertEqual(history[0]["content"], "user-3")
        self.assertEqual(history[-1]["content"], "assistant-4")

    def test_history_respects_character_budget(self) -> None:
        history = [
            {"role": "user", "content": "a" * 80},
            {"role": "assistant", "content": "b" * 80},
            {"role": "user", "content": "short"},
            {"role": "assistant", "content": "reply"},
        ]
        trimmed = trim_history(history, max_messages=10, max_chars=50)

        self.assertEqual([item["content"] for item in trimmed], ["short", "reply"])

    def test_telegram_chunks_never_exceed_limit(self) -> None:
        chunks = split_telegram_text("word " * 100, limit=80)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(0 < len(chunk) <= 80 for chunk in chunks))
        self.assertEqual(" ".join(chunks).split(), ("word " * 100).split())


if __name__ == "__main__":
    unittest.main()
