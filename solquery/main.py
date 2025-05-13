# solquery/main.py (relevant parts modified)
from fastapi import FastAPI, HTTPException, Depends
from contextlib import asynccontextmanager
import json # For potential parsing if LLM stringifies JSON

from .core.config import settings
from .schemas.common_schemas import QueryRequest, QueryResponse, ErrorDetail
from .services import data_sources, llm_service 
# Assume portfolio_service and sentiment_service will be called by functions triggered by llm
# For example, get_nft_collection_sentiment tool would trigger a flow involving data_sources and then llm_service.analyze_sentiment_with_llm

# Lifespan function (ensure llm_service.configure_gemini_if_needed() is called)
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"SolQuery starting up...")
    llm_service.configure_gemini_if_needed() # Initialize Gemini configuration
    await data_sources.init_http_client()
    print("HTTP client initialized.")
    yield
    await data_sources.close_http_client()
    print("HTTP client closed.")
    print("SolQuery shutting down.")

app = FastAPI(title="SolQuery", version="0.1.0", lifespan=lifespan)

# Placeholder for default wallet if user context is implemented later
DEFAULT_TEST_WALLET = "3tA8PjUvrep7UT9LNWnHZQmQ5bg646YuZnt7xLiQAXEe" # Use a real address for testing

@app.post("/query", response_model=QueryResponse)
async def handle_query_endpoint(request: QueryRequest):
    print(f"Received query: '{request.query_text}' from user_id: {request.user_id}")

    # user_context might include default wallet_address, etc.
    user_context = {"default_wallet_address": DEFAULT_TEST_WALLET} # Example context

    routing_decision = await llm_service.route_query_with_llm(request.query_text, user_context)

    if routing_decision.get("error"):
        return QueryResponse(
            success=False,
            answer=f"LLM Routing Error: {routing_decision['error']}",
            llm_trace={"routing_decision": routing_decision},
            error=ErrorDetail(type="LLMRoutingError", message=routing_decision['error'])
        )

    actions = routing_decision.get("actions")
    direct_answer = routing_decision.get("direct_answer")
    clarification_needed = routing_decision.get("clarification_needed")

    final_results = []
    data_sources_used = []

    if actions:
        for action in actions:
            tool_name = action.get("tool_name")
            arguments = action.get("arguments", {})
            print(f"LLM wants to call tool: {tool_name} with args: {arguments}")
            data_sources_used.append(f"Tool: {tool_name}")

            action_result = None
            try:
                if tool_name == "get_wallet_portfolio_summary":
                    # Ensure wallet_address is present, fallback to default if logic allows
                    wallet_addr = arguments.get("wallet_address", user_context.get("default_wallet_address"))
                    if not wallet_addr: raise ValueError("Wallet address missing for get_wallet_portfolio_summary")
                    # For this MVP, let's assume get_sol_balance is what portfolio summary means for now
                    action_result = await data_sources.get_sol_balance(wallet_addr)
                    # In a full impl, this would call a portfolio_service.get_summary(wallet_addr) # todo
                
                elif tool_name == "get_detailed_spl_token_balances":
                    wallet_addr = arguments.get("wallet_address", user_context.get("default_wallet_address"))
                    if not wallet_addr: raise ValueError("Wallet address missing for get_detailed_spl_token_balances")
                    # action_result = await portfolio_service.get_spl_balances(wallet_addr) # Placeholder
                    action_result = {"info": f"Mock SPL balances for {wallet_addr}", "tool_args": arguments}
                
                elif tool_name == "get_wallet_nft_collection":
                    wallet_addr = arguments.get("wallet_address") # Extracted by LLM
                    if not wallet_addr: wallet_addr = user_context.get("default_wallet_address")
                    
                    page = arguments.get("page", 1) # LLM could also extract these if needed
                    limit = arguments.get("limit", 50) # Or use a default

                    if not wallet_addr: 
                        action_result = {"error": "Wallet address is required for fetching NFTs and was not provided."}
                    else:
                        action_result = await data_sources.get_nfts_for_wallet(wallet_addr, page=page, limit=limit)
                
                elif tool_name == "get_nft_collection_sentiment":
                    collection_name = arguments.get("collection_name")
                    if not collection_name: raise ValueError("Collection name missing for sentiment analysis")
                    text_about_collection = await data_sources.get_text_for_sentiment_analysis_nft(collection_name)
                    if text_about_collection.get("error"): raise Exception(text_about_collection.get("error"))
                    action_result = await llm_service.analyze_sentiment_with_llm(text_about_collection.get("text"), topic=collection_name)

                elif tool_name == "get_token_sentiment":
                    token_id = arguments.get("token_symbol_or_mint_address")
                    if not token_id: raise ValueError("Token identifier missing for sentiment analysis")
                    # text_about_token = f"The market is buzzing about {token_id} due to new partnerships."
                    text_about_token = await data_sources.get_text_for_sentiment_analysis_token(token_id)
                    if text_about_token.get("error"): raise Exception(text_about_token.get("error"))
                    action_result = await llm_service.analyze_sentiment_with_llm(text_about_token.get("text"), topic=token_id)
                
                elif tool_name == "get_transaction_history":
                    wallet_addr = arguments.get("wallet_address", user_context.get("default_wallet_address"))
                    limit = arguments.get("limit", 10)
                    if not wallet_addr: raise ValueError("Wallet address missing for transaction history")
                    # action_result = await data_sources.get_transaction_history(wallet_addr, limit) # Placeholder
                    action_result = {"info": f"Mock transaction history for {wallet_addr} (limit {limit})", "tool_args": arguments}

                else:
                    action_result = {"error": f"Unknown tool: {tool_name}"}

                if action_result and action_result.get("error"):
                    # Propagate error from the service call
                     final_results.append({tool_name: {"error": action_result["error"], "details": action_result.get("details")}})
                elif action_result:
                    final_results.append({tool_name: action_result})

            except Exception as e:
                print(f"Error executing tool {tool_name}: {e}")
                final_results.append({tool_name: {"error": f"Execution failed: {str(e)}"}})
        
        if not final_results: # Should not happen if actions were present and handled
            return QueryResponse(success=False, answer="LLM suggested actions, but execution yielded no results.", llm_trace=routing_decision, error=ErrorDetail(type="ExecutionError", message="No results from actions"))
        
        # For MVP, just return the raw results. Later, could send to LLM for summarization.
        return QueryResponse(
            success=True,
            answer={"aggregated_results": final_results} if len(final_results) > 1 else final_results[0], #todo: consider how to format this
            data_source_used=", ".join(data_sources_used) if data_sources_used else "LLM + Various Solana APIs",
            llm_trace={"routing_decision": routing_decision}
        )

    elif clarification_needed:
        return QueryResponse(
            success=True, # Or False depending on how you want to flag this
            answer=clarification_needed,
            data_source_used="LLM (Requesting Clarification)",
            llm_trace={"routing_decision": routing_decision}
        )
        
    elif direct_answer:
        return QueryResponse(
            success=True,
            answer=direct_answer,
            data_source_used="LLM (Direct Answer)",
            llm_trace={"routing_decision": routing_decision}
        )
    else:
        return QueryResponse(
            success=False,
            answer="LLM could not determine an appropriate action or provide an answer.",
            llm_trace={"routing_decision": routing_decision},
            error=ErrorDetail(type="LLMNoActionError", message="No action determined by LLM")
        )