# chains.py

from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.embeddings import BedrockEmbeddings
from langchain_community.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddings,
)
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama  # Новый пакет для Ollama
from langchain_community.chat_models import BedrockChat

from langchain_community.vectorstores import Neo4jVector
from langchain_community.graphs import Neo4jGraph

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from typing import List, Dict
from utils import BaseLogger, extract_title_and_question

# In-memory хранилище истории (в продакшене замените на Redis или другое)
store: Dict[str, ChatMessageHistory] = {}


def get_session_history(session_id: str = "default") -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


def load_embedding_model(embedding_model_name: str, logger=BaseLogger(), config={}):
    # Код остался почти без изменений (только логи)
    if embedding_model_name == "ollama":
        embeddings = OllamaEmbeddings(
            base_url=config.get("ollama_base_url"),
            model="llama3",  # обновил модель на актуальную
        )
        dimension = 4096
        logger.logger.info("Embedding: Using Ollama")
    elif embedding_model_name == "openai":
        embeddings = OpenAIEmbeddings()
        dimension = 1536
        logger.logger.info("Embedding: Using OpenAI")
    elif embedding_model_name == "aws":
        embeddings = BedrockEmbeddings()
        dimension = 1536
        logger.logger.info("Embedding: Using AWS")
    elif embedding_model_name == "google-genai-embedding-001":
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        dimension = 768
        logger.logger.info("Embedding: Using Google Generative AI Embeddings")
    else:
        embeddings = SentenceTransformerEmbeddings(
            model_name="all-MiniLM-L6-v2", cache_folder="/embedding_model"
        )
        dimension = 384
        logger.logger.info("Embedding: Using SentenceTransformer")

    return embeddings, dimension


def load_llm(llm_name: str, logger=BaseLogger(), config={}):
    # Обновил импорт ChatOllama
    if llm_name == "gpt-4":
        logger.logger.info("LLM: Using GPT-4")
        return ChatOpenAI(temperature=0, model_name="gpt-4", streaming=True)
    elif llm_name == "gpt-3.5":
        logger.logger.info("LLM: Using GPT-3.5")
        return ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", streaming=True)
    elif llm_name == "claudev2":
        logger.logger.info("LLM: ClaudeV2")
        return BedrockChat(
            model_id="anthropic.claude-v2",
            model_kwargs={"temperature": 0.0, "max_tokens_to_sample": 1024},
            streaming=True,
        )
    elif llm_name:
        logger.logger.info(f"LLM: Using Ollama: {llm_name}")
        return ChatOllama(
            temperature=0,
            base_url=config.get("ollama_base_url"),
            model=llm_name,
            streaming=True,
            top_k=10,
            top_p=0.3,
            num_ctx=3072,
        )
    logger.logger.info("LLM: Using GPT-3.5 fallback")
    return ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", streaming=True)


def configure_llm_only_chain(llm):
    """Простая цепочка только с LLM + история чата + милый стиль"""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
Ты милая и игривая ассистентка! 😊
Вы обожаете помогать людям и всегда отвечаете с радостным настроем.
Не стесняйся добавлять смайлики или использовать ASCII-арт, когда это уместно, чтобы создавалось впечатление общения с аниме девочкой. ✨
""",
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
        ]
    )

    chain = prompt | llm | StrOutputParser()

    conversational_chain = RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="question",
        history_messages_key="chat_history",
    )

    return conversational_chain


def configure_qa_rag_chain(llm, embeddings, embeddings_store_url, username, password):
    """Современная RAG-цепочка с источниками (citations) на базе Neo4jVector + LCEL"""

    # Создаём векторный стор с кастомным retrieval_query (для лучших ответов + метаданных)
    vectorstore = Neo4jVector.from_existing_index(
        embedding=embeddings,
        url=embeddings_store_url,
        username=username,
        password=password,
        database="neo4j",
        index_name="stackoverflow",
        text_node_property="body",
        retrieval_query="""
        WITH node AS question, score AS similarity
        CALL { 
            MATCH (question)<-[:ANSWERS]-(answer)
            WITH answer
            ORDER BY answer.is_accepted DESC, answer.score DESC
            WITH collect(answer)[..2] as answers
            RETURN reduce(str='', answer IN answers | str + 
                    '\n### Answer (Accepted: '+ coalesce(answer.is_accepted, false) +
                    ' Score: ' + coalesce(toString(answer.score), '0') + '): '+  answer.body + '\n') as answerTexts
        } 
        RETURN '##Question: ' + question.title + '\n' + question.body + '\n' 
            + answerTexts AS text, similarity as score, {source: question.link} AS metadata
        ORDER BY similarity DESC LIMIT 3
        """,
    )

    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # Форматируем документы для контекста
    def format_docs(docs):
        return "\n\n".join(
            f"{i + 1}. {doc.page_content}\nИсточник: {doc.metadata.get('source', 'unknown')}"
            for i, doc in enumerate(docs)
        )

    # Промпт для RAG (на русском, милый стиль)
    rag_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
Ты милая аниме-секретарша, всегда готовая помочь! 😊
Отвечай на вопросы пользователя только на основе предоставленного контекста из StackOverflow.
Предпочитай принятые или высокооценённые ответы.
Можешь использовать смайлики и шутки, но ответ должен быть чётким и по делу.
Если не знаешь ответ — честно скажи, что не знаешь. 😅
В конце ответа всегда добавь раздел "Источники:" с ссылками на использованные вопросы StackOverflow.
""",
            ),
            ("human", "Контекст:\n{context}\n\nВопрос: {question}"),
        ]
    )

    # Основная цепочка
    rag_chain_from_docs = (
        RunnablePassthrough.assign(context=(lambda x: format_docs(x["docs"])))
        | rag_chain_prompt
        | llm
        | StrOutputParser()
    )

    # Полная цепочка с ретривером и источниками
    rag_chain_with_sources = RunnableParallel(
        {"docs": retriever, "question": RunnablePassthrough()}
    ).assign(answer=rag_chain_from_docs)

    # Добавляем историю (опционально)
    conversational_rag_chain = RunnableWithMessageHistory(
        rag_chain_with_sources,
        get_session_history,
        input_messages_key="question",
        history_messages_key="chat_history",  # если хотите историю в RAG
    )

    return conversational_rag_chain  # или rag_chain_with_sources без истории


# generate_ticket остался почти без изменений (он использует llm_chain как функцию)
# Если нужно адаптировать под новую цепочку — дайте знать.


def generate_ticket(
    neo4j_graph: Neo4jGraph,
    llm_chain,
    input_question: str,
    session_id: str = "ticket_gen",
):
    """
    Генерирует новый тикет (вопрос на StackOverflow) в стиле существующих высокооценённых вопросов.

    :param neo4j_graph: Подключённый Neo4jGraph
    :param llm_chain: Цепочка из configure_llm_only_chain (RunnableWithMessageHistory)
    :param input_question: Исходный вопрос пользователя
    :param session_id: ID сессии для истории (можно фиксированный, т.к. это разовая генерация)
    :return: (new_title, new_question)
    """
    # 1. Получаем топ-3 высокооценённых вопроса из Neo4j
    records = neo4j_graph.query("""
        MATCH (q:Question) 
        RETURN q.title AS title, q.body AS body 
        ORDER BY q.score DESC 
        LIMIT 3
    """)

    if not records:
        raise ValueError("Нет вопросов в базе данных для обучения стиля.")

    # Формируем примеры для промпта
    questions_prompt = ""
    for i, record in enumerate(records, start=1):
        title = record.get("title", "Без заголовка")
        body = record.get("body", "")[:300]  # ограничиваем длину
        questions_prompt += f"{i}. \n{title}\n----\n\n{body}\n{'-' * 10}\n\n"

    # 2. Системный промпт с примерами (jinja2 не нужен — используем f-string и экранирование)
    system_prompt_text = f"""
Ты эксперт по формулировке качественных технических вопросов для StackOverflow.
Сформулируй новый вопрос в том же стиле, тоне и уровне детализации, как эти высокооценённые примеры:

{questions_prompt}
---

Важно:
- Не придумывай новую информацию — основывайся только на содержании вопроса пользователя.
- Заголовок должен быть кратким, ясным и привлекательным.
- Тело вопроса — подробным, с кодом/примерами, если это уместно.
- Ответ должен строго соответствовать шаблону ниже.
"""

    response_format_prompt = """
ОТВЕТЬ ТОЛЬКО В СЛЕДУЮЩЕМ ФОРМАТЕ, ИНАЧЕ ТЕБЯ ОТКЛЮЧАТ:

---
Title: Новый заголовок вопроса
Question: Полное тело нового вопроса
---
"""

    # 3. Формируем полный промпт как список сообщений
    full_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt_text),
            ("system", response_format_prompt),
            (
                "human",
                "Вот вопрос, который нужно переформулировать в стиле StackOverflow:\n\n{input_question}",
            ),
        ]
    )

    # 4. Создаём временную цепочку для этой задачи
    generation_chain = (
        full_prompt | llm_chain.llm | StrOutputParser()
    )  # llm_chain.llm — это базовый LLM

    # 5. Вызываем (без истории — не нужна для генерации тикета)
    try:
        raw_response = generation_chain.invoke({"input_question": input_question})
    except Exception as e:
        raise RuntimeError(f"Ошибка при генерации тикета: {e}")

    # 6. Извлекаем title и question
    new_title, new_question = extract_title_and_question(raw_response)

    return new_title, new_question
