# solquery/main.py
from fastapi import FastAPI, HTTPException, Body
from contextlib import asynccontextmanager
import json
from typing import Dict, Any, Optional, List

from .core.config import settings
from .schemas.common_schemas import QueryRequest, QueryResponse, ErrorDetail, SentimentAnalysisResult
from .schemas.defi_schemas import DeFiPortfolio
from .schemas.nft_schemas import NFTPortfolio
from .services import data_sources, llm_service, portfolio_service as pf_service, sentiment_service as sent_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"SolQuery FastAPI starting up on port {settings.SOLQUERY_FASTAPI_PORT}...")
    await data_sources.init_http_client()
    llm_service.configure_gemini_if_needed() # Configure Gemini on startup
    print("HTTP client and LLM service configured.")
    yield
    await data_sources.close_http_client()
    print("HTTP client closed. SolQuery FastAPI shutting down.")

app = FastAPI(title="SolQuery", version="0.1.0", lifespan=lifespan)

# Use a real address for testing if user_context doesn't provide one
DEFAULT_TEST_WALLET = "3tA8PjUvrep7UT9LNWnHZQmQ5bg646YuZnt7xLiQAXEe" 

@app.post("/query", response_model=QueryResponse)
async def handle_query_endpoint(request: QueryRequest):
    print(f"API: Received query: '{request.query_text}' from user_id: {request.user_id}")

    user_context: Dict[str, Any] = {}
    # Example: if user_id exists, you might fetch their default wallet
    # For now, we can pass a test wallet in context if no address is in query
    # user_context["default_wallet_address"] = request.user_wallet_address or DEFAULT_TEST_WALLET

    routing_decision = await llm_service.route_query_with_llm(request.query_text, user_context)
    llm_trace = {"routing_decision": routing_decision} # For debugging

    if routing_decision.get("error"):
        return QueryResponse(success=False, answer=None, llm_trace=llm_trace, 
                             error=ErrorDetail(type="LLMRoutingError", message=routing_decision['error']))
    if routing_decision.get("clarification_needed"):
        return QueryResponse(success=True, answer=routing_decision["clarification_needed"], 
                             data_source_used="LLM (Clarification)", llm_trace=llm_trace)
    if routing_decision.get("direct_answer"):
        return QueryResponse(success=True, answer=routing_decision["direct_answer"], 
                             data_source_used="LLM (Direct Answer)", llm_trace=llm_trace)

    actions = routing_decision.get("actions")
    if not actions:
        # ... (handle no actions error as before) ...
        return QueryResponse(success=False, answer="LLM did not suggest any actionable steps.", 
                             llm_trace=llm_trace, error=ErrorDetail(type="NoActionError", message="No action determined by LLM"))


    aggregated_results: Dict[str, Any] = {} # Store all results here
    data_sources_used_list: List[str] = []
    any_execution_error_occurred = False

    for action in actions:
        tool_name = action.get("tool_name")
        arguments = action.get("arguments", {})
        data_sources_used_list.append(f"Tool: {tool_name}")
        print(f"API: Executing tool: {tool_name} with args: {arguments}")

        action_response_data: Any = None
        
        try:
            # --- Tool Dispatch Logic ---
            if tool_name == "get_sol_balance":
                wallet_addr = arguments.get("wallet_address", user_context.get("default_wallet_address", DEFAULT_TEST_WALLET))
                action_response_data = await data_sources.get_sol_balance_service(wallet_addr)
            
            elif tool_name == "get_spl_token_balances":
                wallet_addr = arguments.get("wallet_address", user_context.get("default_wallet_address", DEFAULT_TEST_WALLET))
                # This returns a DeFiPortfolio Pydantic model on success
                action_response_data = await pf_service.portfolio_service_instance.get_full_defi_portfolio(wallet_addr)
            
            elif tool_name == "get_nft_holdings":
                wallet_addr = arguments.get("wallet_address", user_context.get("default_wallet_address", DEFAULT_TEST_WALLET))
                limit = arguments.get("limit", 50)
                # This returns an NFTPortfolio Pydantic model on success
                action_response_data = await pf_service.portfolio_service_instance.get_nft_portfolio_details(wallet_addr, limit)
            
            elif tool_name == "find_fukuoka_local_services":
                action_response_data = await data_sources.find_fukuoka_local_services_service(**arguments)
            
            elif tool_name == "get_fukuoka_events":
                action_response_data = await data_sources.get_fukuoka_events_service(**arguments)
            
            elif tool_name == "get_crypto_payment_info":
                action_response_data = await data_sources.get_crypto_payment_info_service(**arguments)
            
            elif tool_name == "get_text_for_sentiment":
                action_response_data = await data_sources.get_text_for_sentiment_service(
                    token_identifier=arguments.get("token_identifier"),
                    nft_collection_name=arguments.get("nft_collection_name")
                )
            
            elif tool_name == "analyze_text_sentiment":
                text_to_analyze = arguments.get("text_to_analyze")
                topic = arguments.get("topic")
                if not text_to_analyze or not topic:
                    raise ValueError("Missing 'text_to_analyze' or 'topic' for analyze_text_sentiment tool.")
                # This will call data_sources.get_text_for_sentiment_service then llm_service.analyze_sentiment_with_llm
                action_response_data = await sent_service.sentiment_service_instance.get_sentiment_for_target(
                    target_identifier=topic, 
                    target_type="token" if arguments.get("token_identifier") else "nft_collection" # Heuristic for type
                )

            elif tool_name == "get_wallet_portfolio_summary":
                wallet_addr = arguments.get("wallet_address", user_context.get("default_wallet_address", DEFAULT_TEST_WALLET))
                defi_part = await pf_service.portfolio_service_instance.get_full_defi_portfolio(wallet_addr)
                nft_part = await pf_service.portfolio_service_instance.get_nft_portfolio_details(wallet_addr)
                # Check for errors from individual portfolio parts
                if hasattr(defi_part, 'model_fields') and hasattr(nft_part, 'model_fields'): # Check if they are Pydantic models (success)
                    action_response_data = {
                        "defi_summary": defi_part.model_dump(exclude_none=True),
                        "nft_summary": nft_part.model_dump(exclude_none=True),
                        "wallet_address": wallet_addr,
                        "overall_summary_text": (
                            f"Portfolio for {wallet_addr}: "
                            f"{defi_part.sol_balance.ui_amount:.4f} SOL. "
                            f"{len(defi_part.token_holdings)} SPL token types. "
                            f"{nft_part.total_nfts_count} NFTs."
                        )
                    }
                else: # Handle if one of the parts returned an error dict
                    errors_collated = []
                    if isinstance(defi_part, dict) and defi_part.get("error"): errors_collated.append(f"DeFi Error: {defi_part['error']}")
                    if isinstance(nft_part, dict) and nft_part.get("error"): errors_collated.append(f"NFT Error: {nft_part['error']}")
                    action_response_data = {"error": "Failed to fetch complete portfolio.", "details": errors_collated if errors_collated else "Unknown portfolio error."}
            else:
                action_response_data = {"error": f"Tool '{tool_name}' not implemented in main.py handler."}

            # After the tool call, check if action_response_data itself is an error dictionary
            # (This applies if the called service function directly returns an error dict, e.g., from data_sources)
            if isinstance(action_response_data, dict) and action_response_data.get("error"):
                aggregated_results[f"{tool_name}_error"] = action_response_data.get("error")
                if action_response_data.get("details"):
                    aggregated_results[f"{tool_name}_error_details"] = action_response_data.get("details")
                any_execution_error_occurred = True
            elif action_response_data is not None:
                # It's a successful response (could be Pydantic model or success dict)
                aggregated_results[tool_name] = action_response_data
            else:
                aggregated_results[tool_name] = "Tool executed but returned no data or an explicit None."
                any_execution_error_occurred = True # Treat no data as a form of issue for overall success

        except Exception as e: # Catch exceptions raised by service functions
            print(f"API: Exception executing tool {tool_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            aggregated_results[f"{tool_name}_execution_error"] = str(e)
            any_execution_error_occurred = True

    if not aggregated_results: # Should only happen if actions list was empty but routing said there were actions
        return QueryResponse(success=False, answer="LLM suggested actions, but execution yielded no results or errors.", 
                             llm_trace=llm_trace, error=ErrorDetail(type="ActionExecutionError", message="No data from actions"))

    # Process final answer for QueryResponse
    final_answer_payload: Any
    if len(actions) == 1 and not any_execution_error_occurred:
        # If single action and no errors collected, the answer is the direct result of that action
        final_answer_payload = next(iter(aggregated_results.values()))
    else: 
        # For multiple actions or if any error occurred, return the full aggregation
        # Pydantic models within aggregated_results will be handled by QueryResponse serialization
        final_answer_payload = aggregated_results
    
    # Determine overall success based on whether any error key was added to aggregated_results
    overall_success = not any_execution_error_occurred and not any("error" in key.lower() for key in aggregated_results)


    return QueryResponse(
        success=overall_success,
        answer=final_answer_payload, # This will be correctly serialized by FastAPI if it's a Pydantic model or dict/list
        data_source_used=", ".join(list(set(data_sources_used_list))), 
        llm_trace=llm_trace,
        error=None if overall_success else ErrorDetail(type="AggregatedError", message="One or more actions had issues. See answer for details.")
    )

# To run: uvicorn solquery.main:app --reload --port {settings.SOLQUERY_FASTAPI_PORT}