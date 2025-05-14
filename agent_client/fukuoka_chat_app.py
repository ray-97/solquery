# agent_client/fukuoka_chat_app.py

# Ensure all necessary imports are at the top of your file:
import streamlit as st
import httpx
import json
import os
import uuid
import asyncio
from dotenv import load_dotenv
from typing import Optional, Type, Dict, Any

from uagents import Agent, Model, Bureau, Context # Make sure Bureau and Context are here

# ...(Keep your existing Configuration and Message Model definitions here)...
# --- Configuration ---
dotenv_path_project_root = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path_project_root):
    load_dotenv(dotenv_path_project_root)
    # print(f"DEBUG fukuoka_chat_app: Loaded .env file from: {dotenv_path_project_root}") # Optional debug
else:
    if load_dotenv():
        # print("DEBUG fukuoka_chat_app: Loaded .env file from current working directory or parent.") # Optional debug
        pass
    else:
        print("DEBUG fukuoka_chat_app: Warning: .env file not found.")


ASI1_MINI_API_URL = os.getenv("ASI1_MINI_API_URL", "https://api.asi1.ai/v1/chat/completions")
ASI1_API_KEY = os.getenv("ASI1_API_KEY")
FUKUOKA_CHAT_UI_AGENT_ADDRESS = os.getenv("FUKUOKA_CHAT_UI_AGENT_ADDRESS")

# ---- Debug Print for Loaded Address ----
# print(f"DEBUG fukuoka_chat_app: FUKUOKA_CHAT_UI_AGENT_ADDRESS loaded as: '{FUKUOKA_CHAT_UI_AGENT_ADDRESS}'")

# --- Message Models (must match those in fukuoka_chat_ui_agent.py) ---
class FukuokaQueryForProcessing(Model): # Sent TO fukuoka_chat_ui_agent
    task_id: str
    refined_user_query: str
    original_user_query: str

class FukuokaAgentResponse(Model): # Received FROM fukuoka_chat_ui_agent
    task_id: str
    answer: Optional[str] = None
    structured_answer: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    success: bool = False


async def call_asi1_mini_for_refinement(user_query: str) -> Optional[str]:
    """Calls ASI1-Mini to process the user query for refinement."""
    if not ASI1_API_KEY or "YOUR_ACTUAL_ASI1_MINI_API_KEY_HERE" in ASI1_API_KEY: # Check for placeholder
        st.error("ASI1_API_KEY not configured or is using a placeholder in .env file!")
        return None
    
    system_prompt_for_asi1 = (
         "You are an AI assistant helping a user formulate queries about Fukuoka, Japan, "
        "for topics like local services, crypto payments (Solana, USDC), and regional revitalization. "
        "Your goal is to refine the user's raw query into a clear, actionable question or task description "
        "that a specialized Fukuoka information agent can process effectively. "
        "If the query is already clear, return it as is. If it's too broad, try to make it more specific or indicate what's needed. "
        "For example, if user says 'food in fukuoka', ask 'What kind of food or specific area in Fukuoka are you interested in?'"
    )
    payload = { "model": "asi1-mini", "messages": [ {"role": "system", "content": system_prompt_for_asi1}, {"role": "user", "content": user_query}], "temperature": 0.5, "stream": False, "max_tokens": 200 }
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'Bearer {ASI1_API_KEY}'}

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            st.sidebar.info(f"Streamlit: Calling ASI1-Mini with: {user_query}")
            response = await client.post(ASI1_MINI_API_URL, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()
            refined_query = result.get("choices", [{}])[0].get("message", {}).get("content", user_query.strip())
            if not refined_query: refined_query = user_query.strip()
            st.sidebar.success("Streamlit: ASI1-Mini processed query.")
            st.sidebar.caption(f"Streamlit: Query refined by ASI1-Mini: {refined_query}")
            return refined_query
        except Exception as e:
            st.error(f"Streamlit: Error calling ASI1-Mini: {type(e).__name__} - {e}")
            return user_query # Fallback


async def ask_fukuoka_uagent(task_id: str, original_query: str, refined_query: str) -> FukuokaAgentResponse:
    """
    Sends the refined query to the fukuoka_chat_ui_agent using a temporary uAgent
    and awaits its response.
    """
    if not FUKUOKA_CHAT_UI_AGENT_ADDRESS:
        st.error("FUKUOKA_CHAT_UI_AGENT_ADDRESS not configured in .env file!")
        return FukuokaAgentResponse(task_id=task_id, success=False, error_message="Fukuoka Chat UI Agent address not configured.")

    reply_storage = {}
    temp_agent_name = f"st_query_sender_{task_id.replace('-', '')[:8]}" # Unique name for the temp agent
    
    temp_streamlit_client_agent = Agent(
        name=temp_agent_name,
        seed=f"temp_streamlit_client_seed_{task_id}" # Unique seed for this interaction
    )

    @temp_streamlit_client_agent.on_event("startup")
    async def send_query_to_fukuoka_agent(ctx: Context): # This is the function from the traceback
        # FIX 1: Use temp_streamlit_client_agent.name or ctx.agent.name
        ctx.logger.info(f"StreamlitTempAgent ({temp_streamlit_client_agent.name}, Addr: {temp_streamlit_client_agent.address}): Sending task '{task_id}' to FukuokaChatUIAgent ({FUKUOKA_CHAT_UI_AGENT_ADDRESS})")
        try:
            await ctx.send(
                FUKUOKA_CHAT_UI_AGENT_ADDRESS,
                FukuokaQueryForProcessing(
                    task_id=task_id,
                    refined_user_query=refined_query,
                    original_user_query=original_query
                )
            )
        except Exception as e:
            ctx.logger.error(f"StreamlitTempAgent ({temp_streamlit_client_agent.name}): Failed to send message: {e}")
            reply_storage['result'] = FukuokaAgentResponse(task_id=task_id, success=False, error_message=f"Failed to send task: {str(e)}")
            ctx.signal_stop()

    @temp_streamlit_client_agent.on_message(model=FukuokaAgentResponse, replies=FukuokaQueryForProcessing)
    async def on_fukuoka_agent_reply(ctx: Context, _sender: str, msg: FukuokaAgentResponse):
        ctx.logger.info(f"StreamlitTempAgent ({temp_streamlit_client_agent.name}): Received reply for task '{msg.task_id}'")
        if msg.task_id == task_id:
            reply_storage['result'] = msg
        else:
            ctx.logger.warning(f"StreamlitTempAgent ({temp_streamlit_client_agent.name}): Received reply for mismatched task_id {msg.task_id} (expected {task_id}). Ignoring.")
        ctx.signal_stop() # Stop this temporary agent's bureau

    # FIX 2: Initialize Bureau with port=0 to avoid conflict with other services
    bureau = Bureau(port=8010)
    bureau.add(temp_streamlit_client_agent)

    timeout_duration = 120.0
    bureau_task_completed_normally = False

    try:
        st.sidebar.info(f"Streamlit: Running temp uAgent ({temp_streamlit_client_agent.address}) via Bureau (port will be dynamic)...")
        await asyncio.wait_for(bureau.run_async(), timeout=timeout_duration)
        bureau_task_completed_normally = True
    except asyncio.TimeoutError:
        st.sidebar.error(f"Streamlit: Timed out waiting for reply from FukuokaChatUIAgent for task {task_id}.")
        return FukuokaAgentResponse(task_id=task_id, success=False, error_message="Timeout waiting for Fukuoka Chat UI Agent reply.")
    except Exception as e:
        st.sidebar.error(f"Streamlit: Error during temp agent bureau execution for task {task_id}: {e}")
        import traceback
        traceback.print_exc() # Print full traceback to Streamlit's console
        return FukuokaAgentResponse(task_id=task_id, success=False, error_message=f"Temporary agent bureau error: {str(e)}")
    finally:
        st.sidebar.info(f"Streamlit: Shutting down temp uAgent bureau for task {task_id}...")
        await bureau.shutdown()
        st.sidebar.info(f"Streamlit: Temp uAgent bureau for task {task_id} shutdown.")

    if 'result' in reply_storage:
        return reply_storage['result']
    elif bureau_task_completed_normally:
        st.sidebar.warning(f"Streamlit: Bureau for task {task_id} completed, but no result was captured. Check agent logs for details.")
        return FukuokaAgentResponse(task_id=task_id, success=False, error_message="Processing completed by agent but no specific result captured by UI.")
    else:
        return FukuokaAgentResponse(task_id=task_id, success=False, error_message="No result captured from Fukuoka Chat UI Agent (likely due to earlier error/timeout).")

# ... (handle_user_prompt and Streamlit UI setup as in the previous full version) ...
async def handle_user_prompt(user_prompt: str):
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    
    with st.spinner("Phase 1: Consulting ASI1-Mini for query refinement..."):
        refined_query = await call_asi1_mini_for_refinement(user_prompt)

    if refined_query:
        task_id = str(uuid.uuid4())
        with st.spinner(f"Phase 2: Sending task to Fukuoka AI Assistant (uAgent)..."):
            fukuoka_agent_response: FukuokaAgentResponse = await ask_fukuoka_uagent(task_id, user_prompt, refined_query)

        if fukuoka_agent_response.success:
            # structured_answer from FukuokaAgentResponse should contain SolQuery's full response_data
            solquery_api_response = fukuoka_agent_response.structured_answer 
            if solquery_api_response and isinstance(solquery_api_response, dict):
                answer_content = solquery_api_response.get("answer", "No specific answer content in SolQuery response.")
            else: # Fallback if structured_answer is not a dict or missing
                answer_content = fukuoka_agent_response.answer or "No answer content."

            if isinstance(answer_content, dict): 
                try:
                    display_answer = f"```json\n{json.dumps(answer_content, indent=2)}\n```"
                except TypeError: 
                    display_answer = str(answer_content)
            else:
                display_answer = str(answer_content)
            
            st.session_state.messages.append({"role": "assistant", "content": display_answer})
            if st.sidebar.checkbox("Show Full Response from Fukuoka Agent", key=f"show_raw_{task_id}"):
                st.sidebar.caption("Response from Fukuoka Chat UI Agent (which includes SolQuery's data):")
                st.sidebar.json(fukuoka_agent_response.model_dump()) 
        else:
            error_msg = fukuoka_agent_response.error_message or "Processing failed by Fukuoka AI Assistant."
            st.session_state.messages.append({"role": "assistant", "content": f"Sorry, I encountered an error: {error_msg}"})
    else:
        st.session_state.messages.append({"role": "assistant", "content": "Sorry, I couldn't process your query with ASI1-Mini for refinement."})
    
    st.rerun()

st.set_page_config(page_title="Fukuoka Nomad Assist", layout="wide")
st.title("🌸 Fukuoka Nomad AI Assistant")
st.caption("Powered by SolQuery, Fetch.ai uAgents, and ASI1-Mini")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Konnichiwa! How can I help you find local services or learn about Solana payments in Fukuoka?"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask about Fukuoka, local Solana payments..."):
    asyncio.run(handle_user_prompt(prompt))