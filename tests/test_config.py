from __future__ import annotations

import unittest

from self_tg_approve.config import ConfigError, Settings


BASE_ENV = {
    "TOKEN": "telegram-secret",
    "CHANNEL_ID": "-1001234567890",
    "ADMIN_ID": "123456789",
    "MISTRAL_API_KEY": "mistral-secret",
}


class SettingsTests(unittest.TestCase):
    def test_loads_minimal_configuration(self) -> None:
        settings = Settings.from_env(BASE_ENV)

        self.assertEqual(settings.channel_id, -1001234567890)
        self.assertEqual(settings.admin_id, 123456789)
        self.assertEqual(settings.mistral_model, "mistral-small-latest")
        self.assertEqual(settings.session_history_messages, 12)

    def test_accepts_channel_username_and_allowlist(self) -> None:
        settings = Settings.from_env(
            {
                **BASE_ENV,
                "CHANNEL_ID": "@private_channel",
                "MISTRAL_ALLOWED_USER_IDS": "10, 20,10",
            }
        )

        self.assertEqual(settings.channel_id, "@private_channel")
        self.assertEqual(settings.mistral_allowed_user_ids, frozenset({10, 20}))

    def test_accepts_gemini_key_and_defaults(self) -> None:
        settings = Settings.from_env(
            {
                **BASE_ENV,
                "MISTRAL_API_KEY": "AQ.dummy-key-for-test",
            }
        )

        self.assertEqual(settings.mistral_model, "gemini-3.1-flash-lite")
        self.assertIn("googleapis.com", settings.mistral_api_url)

    def test_fails_fast_for_missing_secret(self) -> None:
        env = {**BASE_ENV, "MISTRAL_API_KEY": ""}
        with self.assertRaisesRegex(ConfigError, "MISTRAL_API_KEY"):
            Settings.from_env(env)

    def test_fails_for_invalid_ids_and_limits(self) -> None:
        with self.assertRaisesRegex(ConfigError, "ADMIN_ID"):
            Settings.from_env({**BASE_ENV, "ADMIN_ID": "admin"})
        with self.assertRaisesRegex(ConfigError, "ADMIN_ID не может совпадать"):
            Settings.from_env(
                {
                    **BASE_ENV,
                    "TOKEN": "123456789:ABCdef-secret",
                    "ADMIN_ID": "123456789",
                }
            )
        with self.assertRaisesRegex(ConfigError, "CHANNEL_ID"):
            Settings.from_env({**BASE_ENV, "CHANNEL_ID": "channel"})
        with self.assertRaisesRegex(ConfigError, "MISTRAL_MAX_TOKENS"):
            Settings.from_env({**BASE_ENV, "MISTRAL_MAX_TOKENS": "99999"})

    def test_repr_does_not_expose_secrets(self) -> None:
        representation = repr(Settings.from_env(BASE_ENV))

        self.assertNotIn("telegram-secret", representation)
        self.assertNotIn("mistral-secret", representation)


if __name__ == "__main__":
    unittest.main()
