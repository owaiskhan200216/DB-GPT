from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.output_parsers import StrOutputParser
from utils import is_ollama_running, start_ollama, stop_ollama

import os
import logging
import sys

sys.path.append("C:/Users/hasan/Desktop/TEXT_WITH_DB/src/LLMs")
sys.path.append("C:/Users/hasan/Desktop/TEXT_WITH_DB/src/DB_connection")

from localmodel import load_local_models
from Mistral import load_mistral_models
from OpenAI import load_OpenAI_model

logger = logging.getLogger("model_server")
app = FastAPI()

LLM1 = None
LLM2 = None


class GenReq(BaseModel):
    prompt: str
    max_tokens: int = 1024
    temperature: float = 0.0


@app.on_event("startup")
def load_model():
    global LLM1, LLM2

    model_type = os.getenv("MODEL_TYPE")
    model_path = os.getenv("MODEL_PATH")

    logger.info(f"Starting model server with MODEL_TYPE={model_type}")

    if model_type == "Local Text2SQL":
        if is_ollama_running():
            stop_ollama()
        LLM1, LLM2 = load_local_models()  
        logger.info("Loaded Local LlamaCpp Text2SQL model")

    elif model_type == "Mistral":
        if is_ollama_running():
            logger.info("Ollama is already running")
        else:
            logger.info("Starting Ollama...")
            start_ollama()    
            if is_ollama_running():
                logger.info("Ollama started successfully")
                LLM1, LLM2 = load_mistral_models()
                logger.info("Loaded Mistral local model")
            else:
                logger.error("Failed to start Ollama")

    elif model_type == "OpenAi":
        if is_ollama_running():
            stop_ollama()
        LLM1, LLM2 = load_OpenAI_model()
        logger.info("Loaded OpenAI models")

    else:
        raise ValueError(f"Invalid MODEL_TYPE: {model_type}")


@app.post("/generate")
def generate(req: GenReq):
    global LLM1

    if LLM1 is None:
        return {"error": "Model not loaded"}
        
    chain = LLM1 | StrOutputParser()

    out = chain.invoke(req.prompt)
    return {"text": out}


