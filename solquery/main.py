# solquery/main.py
from fastapi import FastAPI, HTTPException
from .core.config import settings # Import your settings
from .schemas.common_schemas import QueryRequest, QueryResponse
# Import service modules later as you build them
# from .services import data_sources, llm_service, portfolio_service, sentiment_service

app = FastAPI(title="SolQuery", version="0.1.0")

@app.on_event("startup")
async def startup_event():
    print(f"SolQuery starting up...")
    print(f"Helius API Key Loaded: {'Yes' if settings.HELIUS_API_KEY and settings.HELIUS_API_KEY != 'YOUR_HELIUS_API_KEY_FALLBACK' else 'No/Fallback'}")
    print(f"Gemini API Key Loaded: {'Yes' if settings.GOOGLE_GEMINI_API_KEY and settings.GOOGLE_GEMINI_API_KEY != 'YOUR_GEMINI_API_KEY_FALLBACK' else 'No/Fallback'}")
    # Initialize any global resources here if needed, e.g., httpx.AsyncClient
    

@app.post("/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    print(f"Received query: {request.query_text}")
    # For now, just a placeholder response
    # Later, this will call llm_service.route_query_with_gemini, then data_sources, etc.
    if "balance" in request.query_text.lower():
        # Simulate calling a data source
        # raw_data = await data_sources.get_wallet_balance("some_wallet_address", settings.HELIUS_API_KEY)
        # answer = f"Placeholder balance: 100 SOL. Query was: {request.query_text}"
        answer = "Placeholder: Balance query detected."
        source = "Simulated Solana API"
    else:
        answer = f"Query received: {request.query_text}. No specific action defined yet."
        source = "SolQuery System"

    return QueryResponse(answer=answer, data_source=source)

# To run: uvicorn solquery.main:app --reload