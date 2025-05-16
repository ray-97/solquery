# agent_client/fukuoka_chat_ui_agent.py
import httpx
import asyncio
import json
import os
import uuid
from dotenv import load_dotenv
from typing import Optional, Dict, Any, Tuple

from uagents import Agent, Context, Model, Bureau, Protocol 
from uagents.setup import fund_agent_if_low

# --- Environment & Configuration ---
# (Same .env loading and variable definitions as your last working version)
# Ensure FUKUOKA_CHAT_UI_AGENT_SEED, FUKUOKA_CHAT_UI_AGENT_PORT, HTTP_ENDPOINT_PATH,
# ASI1_MINI_API_URL, ASI1_API_KEY, SOLQUERY_CONNECTOR_AGENT_ADDRESS are loaded.
dotenv_path_project_root = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path_project_root):
    load_dotenv(dotenv_path_project_root)
    print(f"FukuokaChatUIAgent: Loaded .env file from: {dotenv_path_project_root}")
else:
    load_dotenv() 
    print("FukuokaChatUIAgent: Attempted to load .env from current/parent dir.")

FUKUOKA_CHAT_UI_AGENT_SEED = os.getenv("FUKUOKA_CHAT_UI_AGENT_SEED")
FUKUOKA_CHAT_UI_AGENT_PORT = int(os.getenv("FUKUOKA_CHAT_UI_AGENT_PORT", 8002))
HTTP_ENDPOINT_PATH = os.getenv("FUKUOKA_CHAT_UI_AGENT_HTTP_ENDPOINT_PATH", "/ask_fukuoka_assistant").strip()

ASI1_MINI_API_URL = os.getenv("ASI1_MINI_API_URL", "https://api.asi1.ai/v1/chat/completions")
ASI1_API_KEY = os.getenv("ASI1_API_KEY")
SOLQUERY_CONNECTOR_AGENT_ADDRESS = os.getenv("SOLQUERY_CONNECTOR_AGENT_ADDRESS")

# --- Message Models ---
# For uAgent communication with SolQueryConnectorAgent
class ProcessedSolQueryTask(Model):
    task_id: str
    query_for_solquery: str

class SolQueryResult(Model): # Received from SolQueryConnectorAgent
    task_id: str
    success: bool
    response_data: Dict[str, Any] # This is the raw JSON from SolQuery FastAPI
    error_message: Optional[str] = None

# For HTTP communication with Streamlit app
class StreamlitHttpRequest(Model): # Model for request body from Streamlit
    user_query: str

# FukuokaAgentResponse is now implicitly the HTTP response structure (dict, status_code)
# but we can define a Pydantic model for the success case data if desired for clarity.
class FormattedApiResponse(Model): # For the data part of a successful HTTP response
    task_id: str
    natural_language_answer: str
    structured_data: Optional[Dict[str, Any]] = None # Optional: include raw data too
    error_message: Optional[str] = None
    success: bool = True


# --- Agent and Protocol Definition ---
fukuoka_chat_ui_agent = Agent(
    name="fukuoka_chat_ui_backend", # More descriptive name
    seed=FUKUOKA_CHAT_UI_AGENT_SEED,
    port=FUKUOKA_CHAT_UI_AGENT_PORT, 
    endpoint=[f"http://127.0.0.1:{FUKUOKA_CHAT_UI_AGENT_PORT}/submit"] 
)
http_service_protocol = Protocol("FukuokaAssistantHTTPService", version="1.0.1") # Give protocol a version

fund_agent_if_low(fukuoka_chat_ui_agent.wallet.address())
http_client_for_asi1: Optional[httpx.AsyncClient] = None

@fukuoka_chat_ui_agent.on_event("startup")
async def agent_startup(ctx: Context):
    global http_client_for_asi1
    http_client_for_asi1 = httpx.AsyncClient(timeout=60.0)
    # ... (Full startup logging including Agentverse README as before) ...
    ctx.logger.info(f"Fukuoka Chat UI Backend Agent started. HTTP endpoint for Streamlit: POST http://127.0.0.1:{FUKUOKA_CHAT_UI_AGENT_PORT}{HTTP_ENDPOINT_PATH}")


@fukuoka_chat_ui_agent.on_event("shutdown")
async def agent_shutdown(ctx: Context):
    global http_client_for_asi1
    if http_client_for_asi1: await http_client_for_asi1.aclose()
    ctx.logger.info("Fukuoka Chat UI Backend Agent shutting down.")

async def call_asi1_mini_for_query_refinement(ctx: Context, user_query: str) -> Optional[str]:
    if not ASI1_API_KEY or "YOUR_ACTUAL_ASI1_MINI_API_KEY_HERE" in ASI1_API_KEY: # Basic check for placeholder
        ctx.logger.error("ASI1_API_KEY not configured!")
        return None # Or raise an error
    # (ASI1 Mini call logic as previously defined, using http_client_for_asi1)
    system_prompt = ("Refine the user's query about Fukuoka or Solana payments into a clear, actionable task for an information retrieval system. "
                     "Focus on specific entities and intents. If the query is already good, return it. If it's too vague (e.g. 'food'), ask for more details like 'What kind of food or specific area in Fukuoka are you interested in?'")
    payload = {"model": "asi1-mini", "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_query}], "temperature": 0.3, "max_tokens": 150, "stream": False}
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'Bearer {ASI1_API_KEY}'}
    try:
        response = await http_client_for_asi1.post(ASI1_MINI_API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        refined_query = result.get("choices", [{}])[0].get("message", {}).get("content", user_query.strip())
        ctx.logger.info(f"ASI1-Mini refined query to: {refined_query}")
        return refined_query
    except Exception as e:
        ctx.logger.error(f"Error calling ASI1-Mini for refinement: {e}")
        return user_query # Fallback to original query


async def format_solquery_response_with_asi1_mini(ctx: Context, solquery_data: Dict[str, Any], original_query: str) -> str:
    """Uses ASI1-Mini to format the structured SolQuery response into a natural language string."""
    if not ASI1_API_KEY or "YOUR_ACTUAL_ASI1_MINI_API_KEY_HERE" in ASI1_API_KEY:
        ctx.logger.error("ASI1_API_KEY not configured for formatting!")
        return f"Error: ASI1-Mini not available for formatting. Raw data: {json.dumps(solquery_data)}"

    # Create a prompt for ASI1-Mini to summarize/format the data
    prompt_for_formatting = (
        f"You are a helpful assistant. The user asked: '{original_query}'. "
        f"Here is the structured data retrieved to answer their query: \n```json\n{json.dumps(solquery_data, indent=2)}\n```\n"
        "Please present this information to the user in a clear, friendly, and conversational paragraph or a short, well-formatted list if appropriate. "
        "If the data indicates an error or no results (e.g., a message like 'No matching services found'), state that politely. "
        "Do not just repeat the JSON structure. Make it sound natural. For example, if services are found, list them with key details. If a balance is shown, state it clearly."
    )
    payload = {
        "model": "asi1-mini",
        "messages": [{"role": "user", "content": prompt_for_formatting}],
        "temperature": 0.6, "max_tokens": 300, "stream": False # Allow more tokens for a nice summary
    }
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'Bearer {ASI1_API_KEY}'}
    
    try:
        ctx.logger.info(f"Calling ASI1-Mini to format SolQuery response for query: {original_query}")
        response = await http_client_for_asi1.post(ASI1_MINI_API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        formatted_answer = result.get("choices", [{}])[0].get("message", {}).get("content", "Sorry, I couldn't format the information clearly.")
        ctx.logger.info(f"ASI1-Mini formatted answer: {formatted_answer}")
        return formatted_answer
    except Exception as e:
        ctx.logger.error(f"Error calling ASI1-Mini for formatting: {e}")
        return f"I found some information, but had trouble formatting it. Raw data: {json.dumps(solquery_data)}"


# This is how you define an HTTP endpoint handler on a Protocol in uagents
# Make sure your uagents version (0.22.3) supports this way of using @protocol.on_http_request
# If not, we might need to check its specific alternative for defining raw ASGI handlers or similar.
# The error "'Protocol' object has no attribute 'on_http_request'" previously indicated this decorator
# might not be on the Protocol class in v0.22.3.
#
# For v0.22.3, direct HTTP request handling on a custom path on an Agent
# might need a different mechanism if the decorator isn't found.
# The most reliable uAgent interaction from a script is agent-to-agent messaging.
# If this direct HTTP endpoint on the agent is problematic for v0.22.3, the Streamlit app
# would need to use the temporary uAgent pattern to *send a message* to this fukuoka_chat_ui_agent,
# rather than calling it via HTTP.
#
# Let's assume for this iteration that `on_http_request` exists on Protocol for 0.22.3.
# If this line causes an AttributeError, it means this pattern is still not right for v0.22.3.

@http_service_protocol.on_http_request("POST", HTTP_ENDPOINT_PATH, model_body_type=StreamlitHttpRequest)
async def handle_streamlit_query_http(ctx: Context, _sender: str, request: StreamlitHttpRequest) -> Tuple[Dict[str, Any], int]:
    user_query = request.user_query
    ctx.logger.info(f"FukuokaChatUIAgent (HTTP): Received query: {user_query}")
    task_id = str(uuid.uuid4())
    
    # 1. Refine query with ASI1-Mini (optional, could be done in Streamlit too)
    # For this flow, let's assume the user query is what ASI1-Mini would produce, or we call it here.
    # refined_query_for_solquery = await call_asi1_mini_for_query_refinement(ctx, user_query)
    # For simplicity, let's assume the user_query from Streamlit is ready for SolQuery or for further ASI1-Mini processing.
    # Let's assume this agent's job is to take the refined query, get data, then format data.
    # The streamlit app can do the first ASI1 call, then send the refined_query here.
    # So, `user_query` here is assumed to be the `refined_query` from Streamlit.

    query_to_send_to_connector = user_query # Assuming user_query is already refined by Streamlit's ASI1 call

    if not SOLQUERY_CONNECTOR_AGENT_ADDRESS:
        ctx.logger.error("SOLQUERY_CONNECTOR_AGENT_ADDRESS not set!")
        return FormattedApiResponse(task_id=task_id, success=False, error_message="Internal config error.").model_dump(), 500

    try:
        ctx.logger.info(f"FukuokaChatUIAgent: Sending task '{task_id}' to Connector Agent with query: '{query_to_send_to_connector}'")
        connector_response: SolQueryResult = await ctx.send(
            SOLQUERY_CONNECTOR_AGENT_ADDRESS,
            ProcessedSolQueryTask(task_id=task_id, query_for_solquery=query_to_send_to_connector),
            response_type=SolQueryResult,
            timeout=120 
        )

        if connector_response:
            if connector_response.success:
                ctx.logger.info(f"FukuokaChatUIAgent: Got successful structured data from Connector: {connector_response.response_data}")
                # Now, format this structured data using ASI1-Mini
                natural_language_answer = await format_solquery_response_with_asi1_mini(ctx, connector_response.response_data, user_query)
                api_response = FormattedApiResponse(
                    task_id=task_id,
                    natural_language_answer=natural_language_answer,
                    structured_data=connector_response.response_data, # Optionally send raw data too
                    success=True
                )
                return api_response.model_dump(), 200
            else:
                error_msg = connector_response.error_message or "SolQuery Connector reported an unspecified failure."
                ctx.logger.error(f"FukuokaChatUIAgent: Connector Agent failed: {error_msg}")
                return FormattedApiResponse(task_id=task_id, success=False, error_message=error_msg, natural_language_answer=f"Sorry, I couldn't process that: {error_msg}").model_dump(), 500
        else:
            ctx.logger.error(f"FukuokaChatUIAgent: No reply from Connector Agent for task '{task_id}'.")
            return FormattedApiResponse(task_id=task_id, success=False, error_message="No response from backend data agent (timeout).", natural_language_answer="Sorry, I couldn't reach my data sources.").model_dump(), 504

    except Exception as e:
        ctx.logger.error(f"FukuokaChatUIAgent: Error during uAgent/SolQuery interaction: {e}")
        import traceback
        traceback.print_exc()
        return FormattedApiResponse(task_id=task_id, success=False, error_message=f"Internal processing error: {str(e)}", natural_language_answer="Sorry, an unexpected error occurred.").model_dump(), 500

fukuoka_chat_ui_agent.include(http_service_protocol, publish_manifest=True)

if __name__ == "__main__":
    print(f"Starting Fukuoka Chat UI Agent (PID: {os.getpid()})...")
    # ... (other startup print messages as before, ensuring FUKUOKA_CHAT_UI_AGENT_PORT is used)
    bureau = Bureau(port=FUKUOKA_CHAT_UI_AGENT_PORT) # Bureau must run on the agent's configured port
    bureau.add(fukuoka_chat_ui_agent)
    bureau.run()