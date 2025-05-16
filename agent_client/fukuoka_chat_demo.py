# agent_client/fukuoka_chat_demo.py
import streamlit as st
import httpx
import json
import os
import uuid # For unique keys for Streamlit elements if needed
import asyncio
from dotenv import load_dotenv
from typing import Optional, Dict, Any

# --- Configuration ---
# Load .env file from project root, assuming this script is in agent_client/
dotenv_path_project_root = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path_project_root):
    load_dotenv(dotenv_path=dotenv_path_project_root)
    print(f"FukuokaChatDemo: Loaded .env file from: {dotenv_path_project_root}")
else:
    if load_dotenv():
        print("FukuokaChatDemo: Loaded .env file from current working directory or parent.")
    else:
        print("FukuokaChatDemo: Warning: .env file not found. Ensure SOLQUERY_FASTAPI_URL is set if not using default.")

# URL for your SolQuery FastAPI backend
SOLQUERY_FASTAPI_URL = os.getenv("SOLQUERY_FASTAPI_URL", "http://127.0.0.1:8000/query")
# Get the port from the URL for user information, default to 8000 if parsing fails
try:
    SOLQUERY_FASTAPI_PORT_INFO = SOLQUERY_FASTAPI_URL.split(":")[2].split("/")[0]
except:
    SOLQUERY_FASTAPI_PORT_INFO = "8000 (default)"


# --- Async Function to Call SolQuery FastAPI ---
async def call_solquery_directly(user_query: str) -> Dict[str, Any]:
    """
    Sends the user query directly to the SolQuery FastAPI backend
    and returns its JSON response.
    """
    if not SOLQUERY_FASTAPI_URL:
        return {"success": False, "answer": None, "error": {"message": "SolQuery FastAPI URL not configured."}}

    payload = {
        "query_text": user_query,
        "user_id": "streamlit_demo_user" # You can make this more dynamic if needed
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client: # Generous timeout
        try:
            st.sidebar.info(f"DEMO MODE: Sending query directly to SolQuery FastAPI: '{user_query}' at {SOLQUERY_FASTAPI_URL}")
            response = await client.post(SOLQUERY_FASTAPI_URL, json=payload)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            
            result_json = response.json()
            st.sidebar.success("DEMO MODE: Received response from SolQuery FastAPI.")
            st.sidebar.json(result_json) # Show raw response in sidebar for debugging
            return result_json # This is the full response from SolQuery (QueryResponse model)

        except httpx.HTTPStatusError as e:
            error_message = f"SolQuery API HTTP error: {e.response.status_code} - {e.response.text}"
            st.sidebar.error(error_message)
            return {"success": False, "answer": None, "error": {"message": error_message, "type": "HTTPStatusError"}}
        except httpx.RequestError as e:
            error_message = f"SolQuery API request error (network issue): {str(e)}"
            st.sidebar.error(error_message)
            return {"success": False, "answer": None, "error": {"message": error_message, "type": "RequestError"}}
        except Exception as e:
            error_message = f"Unexpected error calling SolQuery API: {str(e)}"
            st.sidebar.error(error_message)
            import traceback
            traceback.print_exc() # Print full traceback to console
            return {"success": False, "answer": None, "error": {"message": error_message, "type": "UnexpectedError"}}


async def handle_user_prompt_direct_to_solquery(user_prompt: str):
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    
    with st.spinner("Fukuoka AI Assistant is thinking... (Querying SolQuery backend directly)"):
        solquery_response = await call_solquery_directly(user_prompt)

    if solquery_response:
        # For debugging, let's see the actual response SolQuery sent
        st.sidebar.caption("Raw response from SolQuery FastAPI:")
        st.sidebar.json(solquery_response)

        if solquery_response.get("success", False): 
            answer_content = solquery_response.get("answer", "No specific answer content found in SolQuery response.")
            llm_trace_info = solquery_response.get("llm_trace")

            if answer_content is None:
                display_answer = "SolQuery processed the request but returned no specific answer data."
            elif isinstance(answer_content, dict): 
                try:
                    display_answer = f"```json\n{json.dumps(answer_content, indent=2)}\n```"
                except TypeError: 
                    display_answer = str(answer_content)
            else: 
                display_answer = str(answer_content)
            
            st.session_state.messages.append({"role": "assistant", "content": display_answer})
            
            # Optional: Show LLM trace if available and checkbox is ticked
            # (Consider if key needs to be more unique if multiple queries happen quickly)
            if st.sidebar.checkbox("Show LLM Routing Trace", key=f"show_llm_trace_{str(uuid.uuid4())[:4]}"):
                if llm_trace_info:
                    st.sidebar.caption("LLM Routing Decision from SolQuery:")
                    st.sidebar.json(llm_trace_info)
                else:
                    st.sidebar.caption("No LLM trace available in this response.")

        else: # success is False or not present
            error_value_from_response = solquery_response.get("error") # Get the value of the 'error' key

            # FIX: Ensure error_info is always a dictionary
            if isinstance(error_value_from_response, dict):
                error_info = error_value_from_response
            else: 
                # Handles if "error" key is missing, or its value is None, or not a dict
                error_info = {"message": "Processing failed with an unspecified or malformed error structure from SolQuery."}
                if error_value_from_response is not None: # If "error" key existed but wasn't a dict
                    error_info["original_error_value_type"] = str(type(error_value_from_response))
                    error_info["original_error_value_str"] = str(error_value_from_response)[:200] # Add original value safely

            error_msg = error_info.get("message", "An unknown error occurred.") # Now error_info is guaranteed to be a dict
            
            # Safely get details if error_info is a dict and has 'details'
            details = error_info.get("details")
            if details:
                error_msg += f" Details: {str(details)[:200]}..." # Show some details
            
            st.session_state.messages.append({"role": "assistant", "content": f"Sorry, I encountered an error: {error_msg}"})
    else:
        # This case means call_solquery_directly itself returned None (e.g., if URL was not configured)
        st.session_state.messages.append({"role": "assistant", "content": "Sorry, there was no response received from the SolQuery service at all."})
    
    st.rerun()

# --- Streamlit UI Setup --- (Same as before)
st.set_page_config(page_title="Fukuoka Nomad Assist (DEMO)", layout="wide")
st.title("🌸 Fukuoka Nomad AI Assistant (SolQuery Direct Demo)")
st.caption(f"This demo is powered by SolQuery FastAPI backend.")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Konnichiwa! How can I help you with Fukuoka or Solana? (Demo mode)"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# Accept user input
if prompt := st.chat_input("Ask about Fukuoka, local Solana payments, or your SOL/USDC balance..."):
    asyncio.run(handle_user_prompt_direct_to_solquery(prompt))