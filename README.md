# Self TG Approve

[![Quality](https://github.com/karnaksp/self-tg-approve/actions/workflows/quality.yml/badge.svg)](https://github.com/karnaksp/self-tg-approve/actions/workflows/quality.yml)

Telegram-бот для approval flow доступа в канал: local LLM support, эксперименты с LangChain/RAG, Neo4j-backed memory, n8n workflow automation и упаковка через Docker Compose.

Это вторичный портфельный проект. Он показывает AI automation и backend integration вокруг Telegram workflows, но не позиционируется как главный Data Engineering showcase.

![Bot screenshot](images/image.png)

## Что делает проект

- Принимает Telegram access requests для приватного канала.
- Позволяет владельцу канала approve или reject заявки.
- Поддерживает conversational AI через Ollama/local LLM components.
- Использует Neo4j для graph-backed session memory и RAG experiments.
- Включает optional n8n workflow import для локальных automation experiments.
- Запускается как multi-service Docker Compose stack.

## Stack

- Python
- python-telegram-bot
- LangChain
- Ollama
- Neo4j
- n8n
- PostgreSQL for n8n
- Docker Compose

## Архитектура

```text
Telegram user
    |
    v
telegram_bot service
    |
    +--> owner approval flow
    |
    +--> api service
             |
             +--> Ollama / local LLM
             +--> LangChain RAG chain
             +--> Neo4j memory graph

n8n + Postgres — optional workflow automation services.
```

## Быстрый старт

```bash
cp .env.example .env
# edit .env: Telegram token, channel id, admin id, local passwords
docker compose up --build
```

Если на машине мало места, heavy images можно собрать отдельно:

```bash
docker compose build pull-model
docker compose build api
docker compose build telegram_bot
docker compose up -d
```

## Конфигурация

Используйте `.env.example` как единственный configuration template, который хранится в git.

Обязательные значения:

- `TOKEN` - Telegram bot token.
- `CHANNEL_ID` - target channel id.
- `ADMIN_ID` - Telegram user id, который может approve requests.
- `POSTGRES_PASSWORD`, `N8N_ENCRYPTION_KEY`, `N8N_USER_MANAGEMENT_JWT_SECRET` - local service secrets.

Опциональные значения:

- `OPENAI_API_KEY`, `MISTRAL_API_KEY`, `GOOGLE_API_KEY` для cloud LLM experiments.
- `LANGCHAIN_API_KEY` для LangChain tracing.
- `LLM` и `EMBEDDING_MODEL` для выбора local model.

## Security notes

- Не коммитьте `.env`.
- Не коммитьте n8n exported credentials. Каталог `n8n/demo-data/credentials/` специально оставлен пустым.
- Если credentials экспортируются для локальных экспериментов, держите их вне git или sanitise перед передачей.
- Закоммиченные workflow JSON не должны содержать active tokens или secrets личных аккаунтов.

## Quality gate

Перед изменениями в Compose stack или exported workflow files запускайте те же lightweight checks, что используются в GitHub Actions:

```bash
python scripts/validate_project.py
cp .env.example .env
docker compose --env-file .env.example config --quiet
rm -f .env
```

Gate проверяет env-template hygiene, n8n workflow JSON, Python syntax и Docker Compose config. Репозиторий намеренно исключает generated Python bytecode, local databases, virtual environments и n8n credential exports.
