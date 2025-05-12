# solquery/schemas/common_schemas.py
from pydantic import BaseModel
from typing import Any, Dict

class QueryRequest(BaseModel):
    query_text: str
    user_id: str | None = None # Optional: if you want to track users

class QueryResponse(BaseModel):
    answer: str | Dict[str, Any] # Could be a simple string or structured data
    data_source: str | None = None
    llm_debug_info: str | None = None # For debugging LLM interaction