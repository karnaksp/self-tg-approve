#!/usr/bin/env python3
"""Fast repository hygiene checks for the lightweight release."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ENV_KEYS = {
    "TOKEN",
    "CHANNEL_ID",
    "ADMIN_ID",
    "MISTRAL_API_KEY",
    "MISTRAL_MODEL",
}
PLACEHOLDER_VALUES = {
    "",
    "your_telegram_bot_token",
    "your_mistral_api_key",
}
FORBIDDEN_RUNTIME_TERMS = {
    "ollama",
    "langchain",
    "sentence_transformers",
    "n8n",
    "pandas",
    "matplotlib",
    "moviepy",
}


def parse_env_example(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
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
        failures.append(f".env.example is missing: {', '.join(missing)}")

    for key, value in values.items():
        secret_like = key.endswith(("KEY", "TOKEN", "PASSWORD", "SECRET"))
        if secret_like and value not in PLACEHOLDER_VALUES:
            failures.append(f".env.example contains a non-placeholder secret: {key}")
    return failures


def validate_requirements() -> list[str]:
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    return [
        f"requirements.txt must not contain heavyweight dependency: {term}"
        for term in sorted(FORBIDDEN_RUNTIME_TERMS)
        if term in requirements
    ]


def validate_python_syntax() -> list[str]:
    failures: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        if any(
            part in {".git", ".venv", "venv", "myenv", "__pycache__"}
            for part in path.parts
        ):
            continue
        try:
            source = path.read_text(encoding="utf-8")
            compile(source, str(path), "exec")
        except (OSError, SyntaxError, UnicodeError) as exc:
            failures.append(f"{path.relative_to(ROOT)} does not compile: {exc}")
    return failures


def main() -> int:
    failures = [
        *validate_env_template(),
        *validate_requirements(),
        *validate_python_syntax(),
    ]
    if failures:
        print("Project validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Project validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
