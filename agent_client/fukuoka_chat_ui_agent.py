# agent_client/fukuoka_chat_ui_agent.py
import httpx
import asyncio
import json
import os
import uuid
from dotenv import load_dotenv
from typing import Optional, Dict, Any

from uagents import Agent, Context, Model, Bureau # Added Bureau for running
from uagents.setup import fund_agent_if_low

# --- Environment & Configuration ---
dotenv_path_project_root = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path_project_root):
    load_dotenv(dotenv_path_project_root)
    print(f"FukuokaChatUIAgent: Loaded .env file from: {dotenv_path_project_root}")
else:
    load_dotenv() # Fallback
    print("FukuokaChatUIAgent: Attempted to load .env from current/parent dir.")


FUKUOKA_CHAT_UI_AGENT_SEED = os.getenv("FUKUOKA_CHAT_UI_AGENT_SEED")
FUKUOKA_CHAT_UI_AGENT_PORT = int(os.getenv("FUKUOKA_CHAT_UI_AGENT_PORT", 8002)) # For its own uAgent server

ASI1_MINI_API_URL = os.getenv("ASI1_MINI_API_URL", "https://api.asi1.ai/v1/chat/completions")
ASI1_API_KEY = os.getenv("ASI1_API_KEY")
SOLQUERY_CONNECTOR_AGENT_ADDRESS = os.getenv("SOLQUERY_CONNECTOR_AGENT_ADDRESS")

# Critical variable checks
if not FUKUOKA_CHAT_UI_AGENT_SEED or "your_unique_secret_seed" in FUKUOKA_CHAT_UI_AGENT_SEED:
    print("CRITICAL WARNING: FUKUOKA_CHAT_UI_AGENT_SEED is not set properly.")
    FUKUOKA_CHAT_UI_AGENT_SEED = f"fallback_fukuoka_chat_seed_{str(uuid.uuid4())}" # Not for production
if not SOLQUERY_CONNECTOR_AGENT_ADDRESS:
    print("CRITICAL WARNING: SOLQUERY_CONNECTOR_AGENT_ADDRESS not set. Cannot connect to SolQuery Connector.")
if not ASI1_API_KEY or "YOUR_ACTUAL_ASI1_MINI_API_KEY_HERE" in ASI1_API_KEY:
    print("CRITICAL WARNING: ASI1_API_KEY not set or is placeholder. ASI1-Mini calls will fail.")


# --- Message Models for communication ---
# Message from Streamlit's temp agent (via ASI1-Mini processed query)
class FukuokaQueryForProcessing(Model):
    task_id: str
    refined_user_query: str # Query after ASI1-Mini has processed it
    original_user_query: str # For context if needed

# Message this agent sends back to Streamlit's temp agent
class FukuokaAgentResponse(Model):
    task_id: str
    answer: Optional[str] = None
    structured_answer: Optional[Dict[str, Any]] = None # The JSON from SolQuery
    error_message: Optional[str] = None
    success: bool = False

# Message models for talking to solquery_connector_agent
class ProcessedSolQueryTask(Model):
    task_id: str # Can reuse task_id or generate a new sub-task_id
    query_for_solquery: str

class SolQueryResult(Model):
    task_id: str
    success: bool
    response_data: Dict[str, Any]
    error_message: Optional[str] = None


# --- Agent Definition ---
fukuoka_chat_ui_agent = Agent(
    name="fukuoka_chat_processor", # Name for Almanac registration
    seed=FUKUOKA_CHAT_UI_AGENT_SEED,
    port=FUKUOKA_CHAT_UI_AGENT_PORT,
    endpoint=[f"http://127.0.0.1:{FUKUOKA_CHAT_UI_AGENT_PORT}/submit"] # Its uAgent message endpoint
)

fund_agent_if_low(fukuoka_chat_ui_agent.wallet.address())
http_client_for_asi1: Optional[httpx.AsyncClient] = None

@fukuoka_chat_ui_agent.on_event("startup")
async def agent_startup(ctx: Context):
    global http_client_for_asi1
    http_client_for_asi1 = httpx.AsyncClient(timeout=60.0)
    ctx.logger.info(f"Fukuoka Chat Processor Agent started. Name: {fukuoka_chat_ui_agent.name}")
    ctx.logger.info(f"My uAgent Address: {fukuoka_chat_ui_agent.address}")
    ctx.logger.info(f"Listening for uAgent messages on port: {FUKUOKA_CHAT_UI_AGENT_PORT}")
    ctx.logger.info(f"Will connect to SolQuery Connector Agent at: {SOLQUERY_CONNECTOR_AGENT_ADDRESS}")
    # (Log README/Agentverse info as before)

@fukuoka_chat_ui_agent.on_event("shutdown")
async def agent_shutdown(ctx: Context):
    global http_client_for_asi1
    if http_client_for_asi1:
        await http_client_for_asi1.aclose()
    ctx.logger.info("Fukuoka Chat Processor Agent shutting down.")

async def call_asi1_mini_for_fukuoka_agent(ctx: Context, user_query: str) -> Optional[str]:
    # This function is now part of this agent's capabilities
    if not ASI1_API_KEY or "YOUR_ACTUAL_ASI1_MINI_API_KEY_HERE" in ASI1_API_KEY:
        ctx.logger.error("ASI1_API_KEY not configured for uAgent call!")
        return None
    
    system_prompt_for_asi1 = (
         "You are an AI assistant helping a user in Fukuoka. Rephrase their query clearly for a specialized Fukuoka information agent (SolQuery). "
        "Focus on the core task or question about local services, Solana payments, or regional topics. "
        "If the query is about personal wallet balances or specific on-chain data, ensure the query reflects that it needs to be passed to a Solana data expert. "
        "The output should be the refined query string itself, ready to be processed further."
    )
    payload = { "model": "asi1-mini", "messages": [ {"role": "system", "content": system_prompt_for_asi1}, {"role": "user", "content": user_query}], "temperature": 0.5, "stream": False, "max_tokens": 200 }
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'Bearer {ASI1_API_KEY}'}
    
    client_to_use = http_client_for_asi1
    if not client_to_use: ctx.logger.error("ASI1 Mini HTTP client not initialized in Fukuoka Agent!"); return user_query

    try:
        ctx.logger.info(f"FukuokaChatUIAgent: Calling ASI1-Mini with: {user_query}")
        response = await client_to_use.post(ASI1_MINI_API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        refined_query = result.get("choices", [{}])[0].get("message", {}).get("content", user_query.strip())
        ctx.logger.info(f"FukuokaChatUIAgent: ASI1-Mini refined query to: {refined_query}")
        return refined_query
    except Exception as e:
        ctx.logger.error(f"FukuokaChatUIAgent: Error calling ASI1-Mini: {e}")
        return user_query # Fallback

@fukuoka_chat_ui_agent.on_message(model=FukuokaQueryForProcessing)
async def handle_fukuoka_query(ctx: Context, sender: str, msg: FukuokaQueryForProcessing):
    ctx.logger.info(f"Fukuoka Agent: Received query task '{msg.task_id}' from '{sender}': '{msg.original_user_query}'")
    ctx.logger.info(f"Fukuoka Agent: Query refined by ASI1-Mini (expected): '{msg.refined_user_query}'")

    final_answer_text = None
    final_structured_answer = None
    final_success = False
    error_text = None

    if not SOLQUERY_CONNECTOR_AGENT_ADDRESS:
        error_text = "SolQuery Connector Agent address not configured for Fukuoka Agent."
        ctx.logger.error(error_text)
    else:
        try:
            ctx.logger.info(f"Fukuoka Agent: Forwarding to SolQuery Connector Agent ({SOLQUERY_CONNECTOR_AGENT_ADDRESS}) task '{msg.task_id}'")
            # Send to SolQueryConnectorAgent and await its specific reply type
            connector_response: SolQueryResult = await ctx.send(
                SOLQUERY_CONNECTOR_AGENT_ADDRESS,
                ProcessedSolQueryTask(task_id=msg.task_id, query_for_solquery=msg.refined_user_query),
                response_type=SolQueryResult, # Expect this model back
                timeout=110 # Slightly less than Streamlit app's overall timeout
            )

            if connector_response:
                ctx.logger.info(f"Fukuoka Agent: Received reply from Connector for task '{msg.task_id}'. Success: {connector_response.success}")
                if connector_response.success:
                    final_structured_answer = connector_response.response_data # This is the full JSON from SolQuery FastAPI
                    # Extract a text answer if possible, or summarize
                    answer_from_solquery = final_structured_answer.get("answer")
                    if isinstance(answer_from_solquery, dict):
                        final_answer_text = json.dumps(answer_from_solquery) # Or a summary
                    else:
                        final_answer_text = str(answer_from_solquery)
                    final_success = True
                else:
                    error_text = connector_response.error_message or "SolQuery Connector reported failure."
            else:
                error_text = "No response or timeout from SolQuery Connector Agent."
                ctx.logger.error(f"Fukuoka Agent: {error_text} for task {msg.task_id}")

        except Exception as e:
            error_text = f"Error in Fukuoka Agent during SolQueryConnector interaction: {str(e)}"
            ctx.logger.error(f"Fukuoka Agent: {error_text} for task {msg.task_id}")
            import traceback
            traceback.print_exc()

    # Send the final response back to the sender (Streamlit's temporary agent)
    await ctx.send(sender, FukuokaAgentResponse(
        task_id=msg.task_id,
        answer=final_answer_text,
        structured_answer=final_structured_answer,
        error_message=error_text,
        success=final_success
    ))

if __name__ == "__main__":
    # ... (print statements)
    bureau = Bureau(
        port=FUKUOKA_CHAT_UI_AGENT_PORT,
        # Providing the /submit endpoint for the bureau is standard
        endpoint=[f"http://127.0.0.1:{FUKUOKA_CHAT_UI_AGENT_PORT}/submit"] 
    )
    bureau.add(fukuoka_chat_ui_agent)
    bureau.run()