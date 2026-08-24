from __future__ import annotations

import logging
import unittest

from self_tg_approve.app import SENSITIVE_NETWORK_LOGGERS, configure_logging


class LoggingTests(unittest.TestCase):
    def test_sensitive_network_loggers_never_use_info_or_debug(self) -> None:
        root_logger = logging.getLogger()
        original_root_level = root_logger.level
        original_levels = {
            name: logging.getLogger(name).level for name in SENSITIVE_NETWORK_LOGGERS
        }
        self.addCleanup(root_logger.setLevel, original_root_level)
        for name, level in original_levels.items():
            self.addCleanup(logging.getLogger(name).setLevel, level)

        configure_logging("DEBUG")
        for logger_name in SENSITIVE_NETWORK_LOGGERS:
            with self.subTest(logger=logger_name):
                self.assertGreaterEqual(
                    logging.getLogger(logger_name).getEffectiveLevel(),
                    logging.WARNING,
                )


if __name__ == "__main__":
    unittest.main()
