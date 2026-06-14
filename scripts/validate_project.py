#!/usr/bin/env python3
"""Lightweight repository quality checks for the portfolio automation project."""

from __future__ import annotations

import json
import os
import py_compile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ENV_KEYS = {
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "N8N_ENCRYPTION_KEY",
    "N8N_USER_MANAGEMENT_JWT_SECRET",
    "LLM",
    "EMBEDDING_MODEL",
    "TOKEN",
    "CHANNEL_ID",
    "ADMIN_ID",
}
PLACEHOLDER_VALUES = {
    "",
    "change_me",
    "change_me_32_chars_minimum",
    "change_me_jwt_secret",
    "your_telegram_bot_token",
    "your_channel_id",
    "your_telegram_user_id",
}


def parse_env_example(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def validate_env_template() -> list[str]:
    values = parse_env_example(ROOT / ".env.example")
    failures: list[str] = []
    missing = sorted(REQUIRED_ENV_KEYS - set(values))
    if missing:
        failures.append(f".env.example is missing keys: {', '.join(missing)}")

    secret_like_keys = [
        key
        for key in values
        if key.endswith("KEY")
        or key.endswith("SECRET")
        or key.endswith("TOKEN")
        or key.endswith("PASSWORD")
    ]
    for key in secret_like_keys:
        value = values[key]
        if value and value not in PLACEHOLDER_VALUES:
            failures.append(f".env.example contains a non-placeholder secret-like value: {key}")
    return failures


def validate_n8n_credentials() -> list[str]:
    credential_dir = ROOT / "n8n" / "demo-data" / "credentials"
    json_files = sorted(path.name for path in credential_dir.glob("*.json"))
    if json_files:
        return [f"n8n credential JSON files must not be committed: {', '.join(json_files)}"]
    return []


def validate_workflow_json() -> list[str]:
    failures: list[str] = []
    for path in sorted((ROOT / "n8n" / "demo-data" / "workflows").glob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{path.relative_to(ROOT)} is invalid JSON: {exc}")
    return failures


def validate_python_syntax() -> list[str]:
    failures: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in {".git", "myenv", "venv", "__pycache__"} for part in path.parts):
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            failures.append(f"{path.relative_to(ROOT)} does not compile: {exc.msg}")
    return failures


def main() -> int:
    failures = []
    failures.extend(validate_env_template())
    failures.extend(validate_n8n_credentials())
    failures.extend(validate_workflow_json())
    failures.extend(validate_python_syntax())

    if failures:
        print("Project validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Project validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
