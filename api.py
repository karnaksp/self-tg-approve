import os

from dotenv import load_dotenv
from utils import (
    BaseLogger,
)
from chains import (
    load_llm,
    configure_llm_only_chain,
)
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

load_dotenv(".env")
logger = BaseLogger()
ollama_base_url = os.getenv("OLLAMA_BASE_URL")
llm_name = os.getenv("LLM")
llm = load_llm(
    llm_name, logger=BaseLogger(), config={"ollama_base_url": ollama_base_url}
)
llm_chain = configure_llm_only_chain(llm)

app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/query")
async def ask(text: str = Query(...), history: Optional[str] = None, rag: bool = False):
    output_function = llm_chain
    result = output_function({"question": text, "chat_history": history}, callbacks=[])

    return {"result": result["answer"], "model": llm_name}
