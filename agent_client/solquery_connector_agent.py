import httpx
import asyncio
import json
import os
from dotenv import load_dotenv
from typing import Optional, Dict, Any # Ensure these are imported for type hints

from uagents import Agent, Context, Model
from uagents.setup import fund_agent_if_low

# --- Environment & Configuration ---
# Load .env file from project root, assuming this script is in agent_client/
dotenv_path_project_root = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path_project_root):
    load_dotenv(dotenv_path_project_root)
    print(f"Loaded .env file from: {dotenv_path_project_root}")
else:
    # Fallback if script is run from project_root or .env is elsewhere
    if load_dotenv(): 
        print("Loaded .env file from current working directory or parent.")
    else:
        print("Warning: .env file not found. Please ensure environment variables are set.")


SOLQUERY_FASTAPI_URL = os.getenv("SOLQUERY_FASTAPI_URL", "http://127.0.0.1:8000/query")
CONNECTOR_AGENT_SEED = os.getenv("CONNECTOR_AGENT_SEED") # Must be set in .env
CONNECTOR_AGENT_PORT = int(os.getenv("SOLQUERY_CONNECTOR_AGENT_PORT", 8001))

if not CONNECTOR_AGENT_SEED or "solquery_connector_agent_secret_seed_phrase" in CONNECTOR_AGENT_SEED:
    print("CRITICAL WARNING: CONNECTOR_AGENT_SEED is not set or is using a default placeholder in your .env file.")
    print("Please generate a unique seed for this agent for it to have a stable identity.")
    # Consider exiting if seed is not secure/unique for a real deployment
    # For hackathon, ensure you've changed it from the very first placeholder.

# --- Message Models ---
# These should match the definitions in fukuoka_chat_app.py
class ProcessedSolQueryTask(Model):
    task_id: str
    query_for_solquery: str

class SolQueryResult(Model):
    task_id: str
    success: bool
    response_data: Dict[str, Any] # To hold the full JSON response from SolQuery FastAPI
    error_message: Optional[str] = None

# --- Agent Definition ---
solquery_connector_agent = Agent(
    name="solquery_connector",
    seed=CONNECTOR_AGENT_SEED,
    port=CONNECTOR_AGENT_PORT,
    endpoint=[f"http://127.0.0.1:{CONNECTOR_AGENT_PORT}/submit"]
)

# Fund the agent if its Almanac contract balance is low (optional, good practice)
fund_agent_if_low(solquery_connector_agent.wallet.address())

# Shared HTTP client for this agent
http_client_instance: Optional[httpx.AsyncClient] = None

@solquery_connector_agent.on_event("startup")
async def initialize_http_client_and_log_readme(ctx: Context):
    global http_client_instance
    http_client_instance = httpx.AsyncClient(timeout=120.0) # Increased timeout for SolQuery processing
    ctx.logger.info(f"SolQuery Connector Agent started. HTTP client initialized.")
    ctx.logger.info(f"SolQuery FastAPI URL: {SOLQUERY_FASTAPI_URL}")
    ctx.logger.info(f"My Agent Address: {solquery_connector_agent.address}")
    ctx.logger.info(f"Listening on effective port (check uvicorn/agent logs for actual bound port if port was 0, aiming for {CONNECTOR_AGENT_PORT})")
    
    # README / Agentverse Description Content (as per Fetch.ai guidelines)
    ctx.logger.info("--- AGENTVERSE README INFORMATION ---")
    ctx.logger.info("![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)")
    ctx.logger.info("![tag:solana](https://img.shields.io/badge/solana-8A2BE2)")
    ctx.logger.info("![tag:fukuoka](https://img.shields.io/badge/fukuoka-F2A202)")
    ctx.logger.info("![tag:digitalnomad](https://img.shields.io/badge/digitalnomad-4A90E2)")
    ctx.logger.info("![tag:api_connector](https://img.shields.io/badge/api_connector-1E90FF)")
    ctx.logger.info("![tag:data_service](https://img.shields.io/badge/data_service-32CD32)")
    ctx.logger.info("![tag:domain/fukuoka-regional-assistance-connector](https://img.shields.io/badge/domain-fukuoka%2Fregional%2Fassistance%2Fconnector-blueviolet)")
    ctx.logger.info("")
    ctx.logger.info("**Agent Name:** `solquery_connector_agent` (SolQuery Connector for Fukuoka Assist)")
    ctx.logger.info("")
    ctx.logger.info("**Description:**")
    ctx.logger.info("This uAgent acts as a vital bridge and data processing hub for the 'Fukuoka Nomad Assist' ecosystem. Its primary function is to receive specific tasks or processed natural language queries (ideally refined by an initial LLM like Fetch.ai's ASI1-Mini from a user-facing chat interface) related to navigating Fukuoka, Japan, for digital nomads and tourists.")
    ctx.logger.info("The agent specializes in connecting to the 'SolQuery' backend service. SolQuery is an AI-powered engine (using Google Gemini with function calling) that accesses and interprets information regarding:")
    ctx.logger.info("* Local Fukuoka services (e.g., crypto-friendly co-working spaces, cafes, shops – using curated/mocked data for the hackathon).")
    ctx.logger.info("* Guidance on using Solana (SOL, USDC) for payments in the region.")
    ctx.logger.info("* Details on Solana wallets and essential on-chain data like token balances (e.g., for a nomad checking their USDC for local spending).")
    ctx.logger.info("This `solquery_connector_agent` takes these specific tasks, securely queries the SolQuery FastAPI endpoint, and returns the processed information, enabling sophisticated, AI-driven assistance.")
    ctx.logger.info("")
    ctx.logger.info("**Main Functions/Services Provided:**")
    ctx.logger.info("* Accepts processed tasks/queries encapsulated in a `ProcessedSolQueryTask` message.")
    ctx.logger.info("* Reliably interfaces with the external SolQuery FastAPI backend to retrieve and process information.")
    ctx.logger.info("* Returns structured results encapsulated in a `SolQueryResult` message, suitable for relaying back to the originating client or agent.")
    ctx.logger.info("")
    ctx.logger.info("**Input Data Model (What this agent expects to receive):**")
    ctx.logger.info("`class ProcessedSolQueryTask(Model):`")
    ctx.logger.info("    `task_id: str`         # A unique identifier for the task/query session.")
    ctx.logger.info("    `query_for_solquery: str` # The specific query string to be sent to the SolQuery FastAPI backend.")
    ctx.logger.info("")
    ctx.logger.info("**Output Data Model (What this agent returns):**")
    ctx.logger.info("`class SolQueryResult(Model):`")
    ctx.logger.info("    `task_id: str`         # The corresponding task_id from the input.")
    ctx.logger.info("    `success: bool`        # True if SolQuery successfully processed the query, False otherwise.")
    ctx.logger.info("    `response_data: dict`  # The full JSON response received from the SolQuery FastAPI service.")
    ctx.logger.info("    `error_message: Optional[str] = None` # Describes any error encountered.")
    ctx.logger.info("--- END AGENTVERSE README INFORMATION ---")


@solquery_connector_agent.on_event("shutdown")
async def cleanup_http_client(ctx: Context):
    global http_client_instance
    if http_client_instance:
        await http_client_instance.aclose()
    ctx.logger.info("SolQuery Connector Agent shutting down. HTTP client closed.")

@solquery_connector_agent.on_message(model=ProcessedSolQueryTask)
async def query_solquery_backend_service(ctx: Context, sender: str, msg: ProcessedSolQueryTask):
    ctx.logger.info(f"Connector Agent: Received task '{msg.task_id}' from Agent Address '{sender}' to query SolQuery with: '{msg.query_for_solquery}'")

    if not http_client_instance:
        ctx.logger.error("CRITICAL: HTTP Client not available in Connector Agent at message handling time!")
        await ctx.send(sender, SolQueryResult(task_id=msg.task_id, success=False, response_data={}, error_message="Internal error: HTTP client not ready in connector."))
        return

    payload = {"query_text": msg.query_for_solquery, "user_id": sender} # Pass sender as user_id to SolQuery
    
    response_success = False
    response_dict_from_solquery: Dict[str, Any] = {}
    error_msg_str: Optional[str] = None

    try:
        api_response = await http_client_instance.post(SOLQUERY_FASTAPI_URL, json=payload)
        api_response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        
        result_json = api_response.json()
        ctx.logger.info(f"Connector Agent: Response from SolQuery FastAPI: {json.dumps(result_json, indent=2)}")
        
        response_dict_from_solquery = result_json
        response_success = result_json.get("success", False) # SolQuery response schema should have "success"
        
        if not response_success:
            error_detail = result_json.get("error")
            if isinstance(error_detail, dict):
                error_msg_str = error_detail.get("message", "SolQuery service indicated failure.")
            elif isinstance(error_detail, str): # If error is just a string
                error_msg_str = error_detail
            else: # Fallback
                error_msg_str = "SolQuery service indicated failure with an unknown error structure."
            ctx.logger.warning(f"SolQuery service call was not successful: {error_msg_str}")

    except httpx.HTTPStatusError as e:
        error_msg_str = f"SolQuery API HTTP error: {e.response.status_code} - Response: {e.response.text}"
        ctx.logger.error(f"Connector Agent: {error_msg_str}")
    except httpx.RequestError as e: # Catches DNS errors, connection refused, etc.
        error_msg_str = f"SolQuery API request error (network issue): {str(e)}"
        ctx.logger.error(f"Connector Agent: {error_msg_str}")
    except json.JSONDecodeError as e:
        error_msg_str = f"Failed to decode JSON response from SolQuery API: {str(e)}"
        ctx.logger.error(f"Connector Agent: {error_msg_str}")
    except Exception as e:
        error_msg_str = f"Unexpected error calling SolQuery API: {str(e)}"
        ctx.logger.error(f"Connector Agent: {error_msg_str}")
        import traceback
        traceback.print_exc()
    
    # Send the result (success or failure with details) back to the original sender
    await ctx.send(sender, SolQueryResult(
        task_id=msg.task_id,
        success=response_success,
        response_data=response_dict_from_solquery, # Send the full SolQuery response
        error_message=error_msg_str
    ))

if __name__ == "__main__":
    print(f"Starting SolQuery Connector Agent (PID: {os.getpid()})...")
    if not CONNECTOR_AGENT_SEED:
        print("ERROR: CONNECTOR_AGENT_SEED environment variable not set. Agent cannot start.")
    else:
        print(f"Agent Name: {solquery_connector_agent.name}")
        print(f"Agent Address: {solquery_connector_agent.address}")
        print(f"Configured to listen on port: {CONNECTOR_AGENT_PORT}")
        print(f"Will connect to SolQuery FastAPI at: {SOLQUERY_FASTAPI_URL}")
        print("Ensure SolQuery FastAPI is running.")
        print("This agent expects tasks of type 'ProcessedSolQueryTask'.")
        solquery_connector_agent.run()