import sys

sys.path.append("C:/Users/hasan/Desktop/TEXT_WITH_DB/src/LLMs")
sys.path.append("C:/Users/hasan/Desktop/TEXT_WITH_DB/src/DB_connection")

from config import (
    ModelType,
    DatabaseConfig,
    DatabaseResponse,
    ReConfigDB,
    QuestionRequest,
    AnswerResponse,
)
from prompts import (
    correction_prompt,
    get_enhanced_sql_prompt_template,
    question_rephrase,
)
from utils import extract_sql, normalize_sql_quotes, to_text, call_model, is_model_server_running
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from subprocess_manager import start_model_server, stop_model_server
from langchain_core.output_parsers import StrOutputParser
from query_execution import validate_and_execute_query
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from localmodel import load_local_models
from typing import List, Dict, Optional
from Mistral import load_mistral_models
from pydantic import BaseModel, Field
from OpenAI import load_OpenAI_model
from urllib.parse import quote_plus
from db_connect import db_connect
from operator import itemgetter
from dotenv import load_dotenv
import requests
import logging
import asyncio
import uuid
import os

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Text-to-SQL API", version="1.0.0")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for models (loaded once at startup)
CURRENT_MODEL = {"model_type": None}
llm1 = None  # Text2SQL model
llm2 = None  # Answer generation model

# Store active database connections and memories per session
active_sessions: Dict[str, Dict] = {}


@app.post("/connect-database", response_model=DatabaseResponse)
async def connect_database(config: DatabaseConfig):
    """Connect to database and initialize session"""
    try:
        session_id = f"{config.db_type}{config.db_host}{config.db_name}{len(active_sessions)}{uuid.uuid4()}"

        db = db_connect(config)

        # Test connection
        table_names = db.get_usable_table_names()
        if not table_names:
            raise HTTPException(status_code=400, detail="No accessible tables found")

        # Store session data
        active_sessions[session_id] = {
            "db": db,
            "table_names": table_names,
            "db_type": config.db_type,
        }

        logger.info(f"Database connected for session {session_id}")
        logger.info(f"Available tables: {table_names}")

        return DatabaseResponse(
            session_id=session_id,
            status="success",
            message=f"Connected successfully. Available tables: {', '.join(table_names)}",
            table_info=db.table_info,
        )

    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(
            status_code=400, detail=f"Database connection failed: {str(e)}"
        )


@app.post("/reconnect-database", response_model=DatabaseResponse)
async def reconnect_database(config: ReConfigDB):
    """Connect to database and initialize session"""
    try:
        session_id = config.session_id

        db = db_connect(config)

        # Test connection
        table_names = db.get_usable_table_names()
        if not table_names:
            raise HTTPException(status_code=400, detail="No accessible tables found")

        # Store session data
        active_sessions[session_id] = {
            "db": db,
            "table_names": table_names,
            "db_type": config.db_type,
        }

        logger.info(f"Database connected for session {session_id}")
        logger.info(f"Available tables: {table_names}")

        return DatabaseResponse(
            session_id=session_id,
            status="reconnected successfully",
            message=f"Connected successfully. Available tables: {', '.join(table_names)}",
            table_info=db.table_info,
        )

    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(
            status_code=400, detail=f"Database connection failed: {str(e)}"
        )


def ensure_model_runtime(model_type: str, model_path: str = ""):
    """
    Start/stop subprocesses only if model actually changed
    """
    global CURRENT_MODEL

    if CURRENT_MODEL["model_type"] == model_type and is_model_server_running():
        return

    start_model_server(model_type=model_type, model_path=model_path)

    # Update state
    CURRENT_MODEL["model_type"] = model_type


# Modified ask_question endpoint
@app.post("/ask-question", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):

    model_type = request.used_model.model_type

    ensure_model_runtime(model_type=model_type, model_path=os.getenv("MODEL_PATH"))

    """Process user question with validation and self-correction"""
    try:
        if request.session_id not in active_sessions:
            raise HTTPException(
                status_code=404,
                detail="Session not found. Please connect to database first.",
            )

        session_data = active_sessions[request.session_id]
        db = session_data["db"]
        db_type = session_data["db_type"]
        question = request.question

        # Prepare inputs
        inputs = {
            "input": question,
            "table_info": db.table_info,
        }

        # Use enhanced prompt template
        sql_prompt = get_enhanced_sql_prompt_template(db_type)

        rephrase_prompt_text = question_rephrase.format(**inputs)

        rephrased_question_text = call_model(rephrase_prompt_text)

        rephrased_question_text = to_text(rephrased_question_text)

        inputs["input"] = rephrased_question_text

        sql_prompt_text = sql_prompt.format(**inputs)

        raw_sql_output = call_model(sql_prompt_text)

        raw_sql_output = to_text(raw_sql_output)

        initial_query = extract_sql(raw_sql_output)
        initial_query = normalize_sql_quotes(initial_query)

        # Validate and execute with self-correction
        success, query_result, final_query, error_log = validate_and_execute_query(
            initial_query, db, db_type, max_retries=2
        )

        if not success:

            # Log detailed error information
            logger.error(f"Query execution failed after retries: {error_log}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate valid SQL query. Last error: {query_result}",
            )

        # Prepare response
        thinking_text = (
            "..." if not error_log else f"Corrected after {len(error_log)} attempts"
        )

        clean_text = str(query_result)

        return AnswerResponse(
            session_id=request.session_id,
            question=question,
            question_rephrased=rephrased_question_text,
            thinking_text=thinking_text,
            answer=clean_text,
            generated_sql=final_query,
            status="success" if not error_log else "success_after_correction",
            used_model=request.used_model,
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error processing question: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error processing question: {str(e)}"
        )


@app.get("/supported-databases")
async def get_supported_databases():
    """Get list of supported database types"""
    return {
        "supported_databases": [
            {
                "type": "mysql",
                "name": "MySQL",
                "default_port": 3306,
                "requires_credentials": True,
                "description": "MySQL database server",
            },
            {
                "type": "postgresql",
                "name": "PostgreSQL",
                "default_port": 5432,
                "requires_credentials": True,
                "description": "PostgreSQL database server",
            },
            {
                "type": "sqlite",
                "name": "SQLite",
                "default_port": None,
                "requires_credentials": False,
                "description": "SQLite database file (provide full file path)",
            },
            {
                "type": "oracle",
                "name": "Oracle",
                "default_port": 1521,
                "requires_credentials": True,
                "description": "Oracle database server",
            },
            {
                "type": "mssql",
                "name": "SQL Server",
                "default_port": 1433,
                "requires_credentials": True,
                "description": "Microsoft SQL Server",
            },
        ]
    }


@app.get("/sessions")
async def get_active_sessions():
    """Get list of active sessions"""
    sessions = []
    for session_id, data in active_sessions.items():
        sessions.append(
            {
                "session_id": session_id,
                "table_names": data["table_names"],
                "db_type": data["db_type"],
            }
        )
    return {"active_sessions": sessions}


@app.delete("/session/{session_id}")
async def close_session(session_id: str):
    """Close a database session"""
    if session_id in active_sessions:
        del active_sessions[session_id]
        return {"message": f"Session {session_id} closed successfully"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "models_loaded": llm1 is not None and llm2 is not None,
        "active_sessions": len(active_sessions),
    }


if __name__ == "_main_":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
