# agent_client/fukuoka_chat_demo.py
import streamlit as st
import httpx
import json
import os
import uuid
import asyncio
from dotenv import load_dotenv
from typing import Optional, Dict, Any

# --- Configuration ---
dotenv_path_project_root = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path_project_root):
    load_dotenv(dotenv_path=dotenv_path_project_root, override=True) # Override for good measure
    print(f"FukuokaChatDemo: Loaded .env file from: {dotenv_path_project_root}")
else:
    if load_dotenv(override=True):
        print("FukuokaChatDemo: Loaded .env file from current working directory or parent.")
    else:
        print("FukuokaChatDemo: Warning: .env file not found. Ensure API keys and URLs are set.")

# ASI1-Mini Configuration
ASI1_MINI_API_URL = os.getenv("ASI1_MINI_API_URL", "https://api.asi1.ai/v1/chat/completions")
ASI1_API_KEY = os.getenv("ASI1_API_KEY")

# SolQuery FastAPI Backend Configuration
SOLQUERY_FASTAPI_URL = os.getenv("SOLQUERY_FASTAPI_URL", "http://127.0.0.1:8000/query")

# Basic check for essential configs
if not ASI1_API_KEY or "YOUR_ACTUAL_ASI1_MINI_API_KEY_HERE" in ASI1_API_KEY:
    st.error("CRITICAL: ASI1_API_KEY is not configured or is using a placeholder in .env file! ASI1-Mini calls will fail.")
if not SOLQUERY_FASTAPI_URL or "http://127.0.0.1:8000/query" not in SOLQUERY_FASTAPI_URL: # Simple check
    st.warning(f"Warning: SOLQUERY_FASTAPI_URL might not be set correctly. Using: {SOLQUERY_FASTAPI_URL}")


# --- Async Helper Functions ---
async def call_asi1_mini_for_processing(
    system_prompt_content: str, 
    user_content: str, 
    purpose: str = "query refinement"
) -> Optional[str]:
    """Generic function to call ASI1-Mini for different purposes."""
    if not ASI1_API_KEY:
        st.sidebar.error(f"ASI1_API_KEY not configured for {purpose}!")
        return None if purpose == "query refinement" else f"Error: ASI1-Mini key missing for {purpose}."

    payload = {
        "model": "asi1-mini",
        "messages": [
            {"role": "system", "content": system_prompt_content},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.5 if purpose == "query refinement" else 0.7, # Different temp for different tasks
        "stream": False,
        "max_tokens": 200 if purpose == "query refinement" else 400 # Allow more for formatting
    }
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'Bearer {ASI1_API_KEY}'}

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            st.sidebar.info(f"Streamlit: Calling ASI1-Mini for {purpose} with input: '{user_content[:100]}...'")
            response = await client.post(ASI1_MINI_API_URL, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()
            
            processed_text = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if not processed_text and purpose == "query refinement":
                 processed_text = user_content # Fallback to original if refinement yields empty
            
            st.sidebar.success(f"Streamlit: ASI1-Mini successfully processed for {purpose}.")
            st.sidebar.caption(f"ASI1-Mini Output ({purpose}): {processed_text[:150]}...")
            return processed_text
        except Exception as e:
            st.error(f"Streamlit: Error calling ASI1-Mini for {purpose}: {type(e).__name__} - {e}")
            st.sidebar.error(f"ASI1-Mini call for {purpose} failed: {e}")
            return user_content if purpose == "query refinement" else f"Error: Could not complete {purpose} using ASI1-Mini."


async def call_solquery_fastapi(query_text_for_solquery: str) -> Dict[str, Any]:
    """Sends the query directly to the SolQuery FastAPI backend."""
    default_error_response = {"success": False, "answer": None, "error": {"message": "Default error in call_solquery_fastapi."}}
    if not SOLQUERY_FASTAPI_URL:
        st.sidebar.error("SolQuery FastAPI URL not configured.")
        default_error_response["error"]["message"] = "SolQuery FastAPI URL not configured."
        return default_error_response

    payload = {"query_text": query_text_for_solquery, "user_id": "streamlit_direct_demo_user"}
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            st.sidebar.info(f"Streamlit: Sending query to SolQuery FastAPI: '{query_text_for_solquery}' at {SOLQUERY_FASTAPI_URL}")
            response = await client.post(SOLQUERY_FASTAPI_URL, json=payload)
            response.raise_for_status()
            result_json = response.json()
            st.sidebar.success("Streamlit: Received response from SolQuery FastAPI.")
            if st.sidebar.checkbox("Show Raw SolQuery Backend Response", key=f"show_raw_backend_{str(uuid.uuid4())[:4]}", value=False):
                st.sidebar.json(result_json)
            return result_json
        except httpx.HTTPStatusError as e:
            error_message = f"SolQuery API HTTP error: {e.response.status_code} - {e.response.text}"
            st.sidebar.error(error_message)
            default_error_response["error"]["message"] = error_message
            return default_error_response
        except httpx.RequestError as e:
            error_message = f"SolQuery API request error (network issue): {str(e)}"
            st.sidebar.error(error_message)
            default_error_response["error"]["message"] = error_message
            return default_error_response
        except Exception as e:
            error_message = f"Unexpected error calling SolQuery API: {str(e)}"
            st.sidebar.error(error_message)
            import traceback
            traceback.print_exc()
            default_error_response["error"]["message"] = error_message
            return default_error_response


async def handle_user_prompt_simplified_flow(user_prompt: str):
    """
    Handles user prompt: User Input -> ASI1-Mini (refine) -> SolQuery FastAPI -> ASI1-Mini (format) -> Display
    """
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    
    # Step 1: Refine query with ASI1-Mini
    refined_query = user_prompt # Default to user_prompt if ASI1 fails
    with st.spinner("Phase 1: ASI1-Mini refining query..."):
        system_prompt_refinement = (
            "You are an AI assistant. Your task is to refine the user's query about Fukuoka or Solana "
            "into a clear, actionable question or task description suitable for an information retrieval system (SolQuery). "
            "Focus on specific entities and intents. If the query is already clear, return it as is. "
            "If it's too vague (e.g. 'food'), try to make it slightly more specific like 'restaurants in Fukuoka' or ask for more details if essential. "
            "The output should be just the refined query string."
        )
        processed_query_by_asi1 = await call_asi1_mini_for_processing(
            system_prompt_content=system_prompt_refinement,
            user_content=user_prompt,
            purpose="query refinement"
        )
        if processed_query_by_asi1:
            refined_query = processed_query_by_asi1
        else: # Fallback if ASI1 call fails or returns nothing
            st.warning("Could not refine query with ASI1-Mini, using original query.")

    # Step 2: Call SolQuery FastAPI with the (potentially refined) query
    solquery_structured_response = None
    with st.spinner(f"Phase 2: SolQuery backend processing: '{refined_query[:100]}...'"):
        solquery_structured_response = await call_solquery_fastapi(refined_query)

    # Step 3: Format SolQuery's response with ASI1-Mini for user display
    final_display_answer = "Sorry, I encountered an issue processing your request." # Default error message

    if solquery_structured_response:
        if solquery_structured_response.get("success", False):
            solquery_answer_data = solquery_structured_response.get("answer")
            if solquery_answer_data is not None:
                with st.spinner("Phase 3: ASI1-Mini formatting final answer..."):
                    system_prompt_formatting = (
                        "You are a helpful AI assistant. You will be given a user's original question and structured JSON data that was retrieved to answer it. "
                        "Your task is to synthesize this information into a friendly, conversational, and easy-to-understand natural language response for the user. "
                        "If the data contains a list of items (e.g., services, NFTs, tokens), present them clearly, perhaps as a bulleted list or a concise summary. "
                        "If the data indicates an error or 'no results found', state that politely. Do not just repeat the JSON. Make it helpful."
                    )
                    user_content_for_formatting = (
                        f"The user originally asked: '{user_prompt}'\n\n"
                        f"Here's the structured data I found: \n```json\n{json.dumps(solquery_answer_data, indent=2)}\n```\n\n"
                        "Please present this to the user."
                    )
                    formatted_answer_by_asi1 = await call_asi1_mini_for_processing(
                        system_prompt_content=system_prompt_formatting,
                        user_content=user_content_for_formatting,
                        purpose="response formatting"
                    )
                    if formatted_answer_by_asi1:
                        final_display_answer = formatted_answer_by_asi1
                    else: # Fallback if formatting call fails
                        final_display_answer = f"I found some data, but had trouble formatting it. Raw data: {json.dumps(solquery_answer_data, indent=2)}"
            else: # SolQuery success but no "answer" field
                final_display_answer = "SolQuery processed the request, but there's no specific data in the 'answer' field."
        else: # SolQuery success was False
            error_info = solquery_structured_response.get("error", {"message": "SolQuery backend reported an error."})
            error_msg = error_info.get("message", "An unknown error occurred in SolQuery backend.")
            final_display_answer = f"Sorry, I encountered an error from the SolQuery service: {error_msg}"
    else: # No response from SolQuery FastAPI at all
        final_display_answer = "Sorry, I couldn't get any response from the SolQuery backend service."
            
    st.session_state.messages.append({"role": "assistant", "content": final_display_answer})
    st.rerun()

# --- Streamlit UI Setup ---
st.set_page_config(page_title="Fukuoka Nomad Assist (Demo)", layout="wide")
st.title("🌸 Fukuoka Nomad AI Assistant")


if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Konnichiwa! How can I help you with Fukuoka or Solana? (I'll use ASI1-Mini and then SolQuery directly for this demo)"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"]) # Use markdown for better rendering

if prompt := st.chat_input("Ask about Fukuoka, local Solana payments, or your SOL/USDC balance..."):
    asyncio.run(handle_user_prompt_simplified_flow(prompt))