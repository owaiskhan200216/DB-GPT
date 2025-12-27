from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal


class ModelType(BaseModel):
    model_type: Literal["Local Text2SQL", "OpenAi", "Mistral"]


# Pydantic models for request/response
class DatabaseConfig(BaseModel):
    db_type: str = Field(
        ..., description="Database type: mysql, postgresql, sqlite, oracle, mssql"
    )
    db_user: str = Field(
        default="", description="Database username (not required for SQLite)"
    )
    db_password: str = Field(
        default="", description="Database password (not required for SQLite)"
    )
    db_host: str = Field(
        default="localhost", description="Database host (not required for SQLite)"
    )
    db_port: Optional[int] = Field(default=None, description="Database port (optional)")
    db_name: str = Field(..., description="Database name or file path for SQLite")
    table_names: List[str] = Field(..., description="List of table names to include")


class ReConfigDB(BaseModel):
    db_type: str = Field(
        ..., description="Database type: mysql, postgresql, sqlite, oracle, mssql"
    )
    db_user: str = Field(
        default="", description="Database username (not required for SQLite)"
    )
    db_password: str = Field(
        default="", description="Database password (not required for SQLite)"
    )
    db_host: str = Field(
        default="localhost", description="Database host (not required for SQLite)"
    )
    db_port: Optional[int] = Field(default=None, description="Database port (optional)")
    db_name: str = Field(..., description="Database name or file path for SQLite")
    table_names: List[str] = Field(..., description="List of table names to include")
    session_id: str = Field(..., description="Session ID to reconnect")


class QuestionRequest(BaseModel):
    session_id: str
    question: str
    used_model: ModelType


class DatabaseResponse(BaseModel):
    session_id: str
    status: str
    message: str
    table_info: Optional[str] = None


class AnswerResponse(BaseModel):
    session_id: str
    question: str
    question_rephrased: Optional[str] = None
    thinking_text: str
    answer: str
    generated_sql: str
    status: str
    used_model: ModelType
