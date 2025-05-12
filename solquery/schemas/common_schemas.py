# solquery/schemas/common_schemas.py
from pydantic import BaseModel
from typing import Any, Dict, Optional

class QueryRequest(BaseModel):
    query_text: str
    user_id: Optional[str] = None # Optional: if you want to track users
    # You might add more fields later, e.g., specific parameters if LLM extracts them
    # target_address: Optional[str] = None
    # target_token: Optional[str] = None

class ErrorDetail(BaseModel):
    type: str
    message: str

class QueryResponse(BaseModel):
    success: bool = True
    answer: Optional[str | Dict[str, Any]] = None
    data_source_used: Optional[str] = None
    llm_trace: Optional[Dict[str, Any]] = None # For debugging LLM steps
    error: Optional[ErrorDetail] = None

# class QueryResponse(BaseModel):
#     answer: str | Dict[str, Any] # Could be a simple string or structured data
#     data_source: str | None = None
#     llm_debug_info: str | None = None # For debugging LLM interaction