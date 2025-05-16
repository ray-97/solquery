from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List, Union
from .defi_schemas import DeFiPortfolio # Forward reference if defined below or import
from .nft_schemas import NFTPortfolio # Forward reference if defined below or import

class QueryRequest(BaseModel):
    query_text: str
    user_id: Optional[str] = None
    # For future context/personalization:
    # user_wallet_address: Optional[str] = None 
    # conversation_history: Optional[List[Dict[str,str]]] = None

class ErrorDetail(BaseModel):
    type: str
    message: str
    details: Optional[Any] = None

class SentimentAnalysisResult(BaseModel):
    target_name: str
    target_type: str # "nft_collection" or "token"
    sentiment_data: Dict[str, Any] = Field(description="Should contain 'sentiment_classification' and 'justification'")
    source_text_preview: Optional[str] = None

# Forward declaration for QueryResponse answer types
class FukuokaServiceInfo(BaseModel): # Example structure for Fukuoka services
    name: str
    category: str
    address: Optional[str] = None
    accepts_solana_payments: Optional[bool] = None
    details: Optional[str] = None

class FukuokaEventInfo(BaseModel): # Example structure for Fukuoka events
    name: str
    date: str
    description: Optional[str] = None
    accepts_crypto: Optional[bool] = None

class CryptoPaymentInfo(BaseModel):
    topic: str
    information: str

class QueryResponse(BaseModel):
    success: bool = True
    # The answer can be one of many types depending on the query
    answer: Optional[Union[
        DeFiPortfolio, 
        NFTPortfolio, 
        SentimentAnalysisResult,
        List[FukuokaServiceInfo],
        List[FukuokaEventInfo],
        CryptoPaymentInfo,
        Dict[str, Any], # For generic SOL balance, other direct data
        str
    ]] = None
    data_source_used: Optional[str] = None
    llm_trace: Optional[Dict[str, Any]] = None
    error: Optional[ErrorDetail] = None