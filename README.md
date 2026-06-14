# Self TG Approve

[![Quality](https://github.com/karnaksp/self-tg-approve/actions/workflows/quality.yml/badge.svg)](https://github.com/karnaksp/self-tg-approve/actions/workflows/quality.yml)

Telegram access approval bot with local LLM support, LangChain/RAG experiments, Neo4j-backed memory, n8n workflow automation, and Docker Compose packaging.

This is a secondary portfolio project: it demonstrates AI automation and backend integration around Telegram workflows. It is not positioned as a primary Data Engineering showcase.

![Bot screenshot](images/image.png)

## What It Does

- Receives Telegram access requests for a private channel.
- Lets the channel owner approve or reject requests.
- Supports conversational AI through Ollama/local LLM components.
- Uses Neo4j for graph-backed session memory and RAG experiments.
- Includes optional n8n workflow import for local automation experiments.
- Runs as a multi-service Docker Compose stack.

## Stack

- Python
- python-telegram-bot
- LangChain
- Ollama
- Neo4j
- n8n
- PostgreSQL for n8n
- Docker Compose

## Architecture

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

n8n + Postgres are optional workflow automation services.
```

## Quick Start

```bash
cp .env.example .env
# edit .env: Telegram token, channel id, admin id, local passwords
docker compose up --build
```

If the machine has limited disk space, build the heavy images separately:

```bash
docker compose build pull-model
docker compose build api
docker compose build telegram_bot
docker compose up -d
```

## Configuration

Use `.env.example` as the only committed configuration template.

Required values:

- `TOKEN` - Telegram bot token.
- `CHANNEL_ID` - target channel id.
- `ADMIN_ID` - Telegram user id that can approve requests.
- `POSTGRES_PASSWORD`, `N8N_ENCRYPTION_KEY`, `N8N_USER_MANAGEMENT_JWT_SECRET` - local service secrets.

Optional values:

- `OPENAI_API_KEY`, `MISTRAL_API_KEY`, `GOOGLE_API_KEY` for cloud LLM experiments.
- `LANGCHAIN_API_KEY` for LangChain tracing.
- `LLM` and `EMBEDDING_MODEL` for local model selection.

## Security Notes

- Do not commit `.env`.
- Do not commit n8n exported credentials. The `n8n/demo-data/credentials/` directory is intentionally kept empty.
- If credentials are exported for local experiments, keep them outside git or sanitize them before sharing.
- Committed workflow JSON should not contain active tokens or personal account secrets.

## Quality Gate

Run the same lightweight checks used by GitHub Actions before changing the Compose stack or exported workflow files:

```bash
python scripts/validate_project.py
cp .env.example .env
docker compose --env-file .env.example config --quiet
rm -f .env
```

The gate validates env-template hygiene, n8n workflow JSON, Python syntax, and Docker Compose config. The repository intentionally excludes generated Python bytecode, local databases, virtual environments, and n8n credential exports.
