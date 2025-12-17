# api.py

import os
from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from utils import BaseLogger
from chains import (
    load_llm,
    configure_llm_only_chain,
    configure_qa_rag_chain,
    generate_ticket,
    load_embedding_model,
)
from langchain_community.graphs import Neo4jGraph

# Загрузка переменных окружения
load_dotenv(".env")
logger = BaseLogger()

# Конфиг LLM
ollama_base_url = os.getenv("OLLAMA_BASE_URL")
llm_name = os.getenv("LLM", "llama3")  # fallback на llama3

llm = load_llm(llm_name, logger=logger, config={"ollama_base_url": ollama_base_url})

# Основная цепочка — только LLM с историей чата и милым стилем
llm_chain = configure_llm_only_chain(llm)

# === Конфигурация для RAG и генерации тикетов ===
neo4j_url = os.getenv("NEO4J_URL")
neo4j_username = os.getenv("NEO4J_USERNAME")
neo4j_password = os.getenv("NEO4J_PASSWORD")
embedding_model_name = os.getenv("EMBEDDING_MODEL", "ollama")  # ollama, openai, etc.

if not all([neo4j_url, neo4j_username, neo4j_password]):
    logger.logger.warning(
        "Neo4j credentials not provided — RAG and ticket generation will be unavailable."
    )
    rag_chain = None
    neo4j_graph = None
else:
    try:
        # Загружаем эмбеддинги (нужны для Neo4jVector)
        embeddings, _ = load_embedding_model(
            embedding_model_name,
            logger=logger,
            config={"ollama_base_url": ollama_base_url},
        )

        # RAG-цепочка с историей и источниками
        rag_chain = configure_qa_rag_chain(
            llm=llm,
            embeddings=embeddings,
            embeddings_store_url=neo4j_url,
            username=neo4j_username,
            password=neo4j_password,
        )

        # Граф для генерации тикетов (Neo4jGraph — лёгкий клиент для Cypher-запросов)
        neo4j_graph = Neo4jGraph(
            url=neo4j_url,
            username=neo4j_username,
            password=neo4j_password,
        )
        logger.logger.info("Neo4j connected — RAG and ticket generation enabled.")
    except Exception as e:
        logger.logger.error(f"Failed to initialize Neo4j/RAG: {e}")
        rag_chain = None
        neo4j_graph = None

# === FastAPI приложение ===
app = FastAPI(
    title="Аниме-ассистентка с RAG по StackOverflow",
    description="Милая ассистентка с поддержкой Ollama, RAG и генерации вопросов для SO ✨",
    version="1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Приветик! Я твоя милая аниме-ассистентка! 😊✨"}


@app.get("/query")
async def ask(
    text: str = Query(..., description="Вопрос пользователя"),
    session_id: str = Query(
        "default", description="ID сессии для сохранения истории чата"
    ),
):
    """
    Простой чат с LLM (без RAG) — с историей и милым стилем.
    """
    try:
        result = llm_chain.invoke(
            {"question": text}, config={"configurable": {"session_id": session_id}}
        )
        # result — строка (StrOutputParser в конце цепочки)
        return {"result": result, "model": llm_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/query_rag")
async def ask_rag(
    text: str = Query(..., description="Вопрос пользователя"),
    session_id: str = Query(
        "default", description="ID сессии для истории (опционально в RAG)"
    ),
):
    """
    RAG-режим: поиск по StackOverflow + ответ с источниками.
    """
    if rag_chain is None:
        raise HTTPException(
            status_code=503,
            detail="RAG не настроен: отсутствуют переменные окружения для Neo4j или ошибка подключения.",
        )

    try:
        result = rag_chain.invoke(
            {"question": text}, config={"configurable": {"session_id": session_id}}
        )
        # result — dict с ключами: 'answer', 'docs' и 'question'
        answer = result.get("answer", "Не удалось получить ответ 😅")
        return {
            "result": answer,
            "model": llm_name,
            "sources": [
                doc.metadata.get("source")
                for doc in result.get("docs", [])
                if doc.metadata.get("source")
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/generate_ticket")
async def gen_ticket(
    question: str = Query(
        ..., description="Исходный вопрос пользователя для переформулировки"
    ),
    session_id: str = Query(
        "ticket_gen", description="Фиксированная сессия для генерации тикетов"
    ),
):
    """
    Генерация нового вопроса в стиле высокооценённых вопросов StackOverflow.
    """
    if neo4j_graph is None:
        raise HTTPException(
            status_code=503,
            detail="Генерация тикетов недоступна: нет подключения к Neo4j.",
        )

    try:
        new_title, new_question = generate_ticket(
            neo4j_graph=neo4j_graph,
            llm_chain=llm_chain,
            input_question=question,
            session_id=session_id,  # можно оставить default, история не критична
        )
        return {"title": new_title, "question": new_question, "model": llm_name}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Ошибка генерации тикета: {str(e)}"
        )


@app.get("/health")
async def health():
    return {"status": "ok", "llm": llm_name, "rag_available": rag_chain is not None}
