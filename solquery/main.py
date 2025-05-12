from fastapi import FastAPI, HTTPException, Depends
from contextlib import asynccontextmanager

from .core.config import settings
from .schemas.common_schemas import QueryRequest, QueryResponse, ErrorDetail
from .services import data_sources, llm_service, portfolio_service, sentiment_service # portfolio & sentiment are placeholders for now

# Lifespan manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"SolQuery starting up...")
    print(f"Log Level: {settings.LOG_LEVEL}")
    print(f"Default Solana Network: {settings.DEFAULT_SOLANA_NETWORK}")
    
    # Configure Gemini API (safer to do it once here)
    llm_service.configure_gemini_if_needed()
    print(f"Helius API Key Loaded: {'Yes' if settings.HELIUS_API_KEY and 'FALLBACK' not in settings.HELIUS_API_KEY else 'No/Fallback/Not Set Correctly'}")
    # print(f"BitQuery API Key Loaded: {'Yes' if settings.BITQUERY_API_KEY else 'No'}")
    
    await data_sources.init_http_client()
    print("HTTP client initialized.")
    
    yield
    
    # Shutdown
    await data_sources.close_http_client()
    print("HTTP client closed.")
    print("SolQuery shutting down.")

app = FastAPI(title="SolQuery", version="0.1.0", lifespan=lifespan)

# Placeholder for actual wallet address extraction for MVP
# In a real app, this would come from the LLM or user input more directly
TEST_WALLET_ADDRESS = "ReplaceWithRealSolanaAddressForTesting" # e.g., a known whale or your own devnet wallet

@app.post("/query", response_model=QueryResponse)
async def handle_query_endpoint(request: QueryRequest):
    print(f"Received query: '{request.query_text}' from user_id: {request.user_id}")

    llm_routing_result = await llm_service.route_query_with_llm(request.query_text)
    
    if llm_routing_result.get("error"):
        return QueryResponse(
            success=False,
            answer="Could not process query due to LLM routing error.",
            llm_trace=llm_routing_result,
            error=ErrorDetail(type="LLMRoutingError", message=llm_routing_result["error"])
        )

    intent = llm_routing_result.get("intent")
    entities = llm_routing_result.get("entities", {})
    llm_direct_answer = llm_routing_result.get("llm_direct_answer")

    response_data = {}
    data_source_name = "LLM"

    try:
        if intent == "get_balance":
            # For MVP, using a test wallet address. Later, extract from 'entities' or request
            wallet_address = entities.get("wallet_address_placeholder", TEST_WALLET_ADDRESS)
            if "YOUR_WALLET_ADDRESS_HERE" in wallet_address or "ReplaceWithRealSolanaAddress" in wallet_address:
                 print(f"WARNING: Using placeholder or unconfigured test wallet address: {wallet_address}")
            
            balance_data = await data_sources.get_sol_balance(wallet_address)
            if balance_data.get("error"):
                raise Exception(f"Data source error for get_balance: {balance_data['error']}")
            response_data = balance_data
            data_source_name = "Solana RPC (via Helius/Provider)"
        
        elif intent == "get_nfts":
            wallet_address = entities.get("wallet_address_placeholder", TEST_WALLET_ADDRESS)
            if "YOUR_WALLET_ADDRESS_HERE" in wallet_address or "ReplaceWithRealSolanaAddress" in wallet_address:
                 print(f"WARNING: Using placeholder or unconfigured test wallet address: {wallet_address}")

            # This will call the placeholder for now
            nft_data = await data_sources.get_nfts_for_wallet(wallet_address)
            if nft_data.get("error"):
                raise Exception(f"Data source error for get_nfts: {nft_data['error']}")
            response_data = nft_data
            data_source_name = "Solana NFT API (e.g., Helius DAS)"

        elif intent == "get_sentiment":
            topic = entities.get("topic_placeholder", request.query_text) # Use full query as topic if not extracted
            # For MVP, let's analyze the original query text for sentiment
            # In a real scenario, you'd fetch news/social data related to 'topic'
            # and then pass that combined text to the sentiment analyzer.
            sentiment_result = await llm_service.analyze_sentiment_with_llm(topic)
            if sentiment_result.get("error"):
                raise Exception(f"LLM error for get_sentiment: {sentiment_result['error']}")
            response_data = sentiment_result
            data_source_name = "LLM (Gemini for Sentiment)"
            
        elif llm_direct_answer: # Fallback from llm_router
            response_data = {"text": llm_direct_answer}
            data_source_name = "LLM (Gemini Direct)"
            
        else:
            # Fallback if intent is not specifically handled yet by DeFi/NFT services
            response_data = {"info": f"Intent '{intent}' recognized but not yet fully implemented. Entities: {entities}"}
            data_source_name = "SolQuery System (Intent recognized)"

        return QueryResponse(
            success=True,
            answer=response_data,
            data_source_used=data_source_name,
            llm_trace={"routing_intent": intent, "routing_entities": entities}
        )

    except Exception as e:
        print(f"Error processing query: {e}")
        return QueryResponse(
            success=False,
            answer=f"Failed to process query: {str(e)}",
            llm_trace={"routing_intent": intent, "routing_entities": entities},
            error=ErrorDetail(type="ProcessingError", message=str(e))
        )

# To run from parent directory (solquery_project): uvicorn solquery.main:app --reload