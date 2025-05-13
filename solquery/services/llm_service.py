import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold, FunctionCall
from ..core.config import settings
from .tool_definitions import SOLQUERY_TOOL_CONFIG # Import the tool configuration
from typing import Dict, Any, List, Optional, Tuple, Union
import json

_gemini_configured = False
_gemini_model = None

def configure_gemini_if_needed():
    global _gemini_configured, _gemini_model
    if not _gemini_configured:
        if settings.GOOGLE_GEMINI_API_KEY and settings.GOOGLE_GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_FALLBACK":
            try:
                genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
                # Initialize the model once
                _gemini_model = genai.GenerativeModel(
                    model_name='gemini-1.5-flash-latest', # Or 'gemini-1.5-pro-latest'
                    # tools=[SOLQUERY_TOOL_CONFIG], # Pass tools here
                    # safety_settings can be configured here if needed
                    # system_instruction can also be set here
                )
                _gemini_configured = True
                print("Google Gemini API configured successfully with SolQuery tools.")
            except Exception as e:
                print(f"ERROR: Failed to configure Google Gemini API: {e}")
        else:
            print("WARNING: GOOGLE_GEMINI_API_KEY not found or is fallback. LLM service will not function.")

async def route_query_with_llm(user_query: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Uses Gemini's function calling to determine which SolQuery tool(s) to call
    and extracts the necessary arguments.
    Returns a list of actions to take, or a clarification question, or a direct answer.
    """
    configure_gemini_if_needed()
    if not _gemini_model or not _gemini_configured:
        return {"error": "Gemini API not configured. Cannot route query."}

    # Construct messages for the chat, including system instructions and context
    # System instruction can be part of the model initialization or prepended here
    system_instruction = (
        "You are SolQuery, an intelligent AI assistant for the Solana blockchain. "
        "Your primary goal is to help users with DeFi and NFT portfolio management and provide sentiment analysis. "
        "Based on the user's query, you must determine the most appropriate action(s) by selecting one or more of the available tools (functions). "
        "Carefully analyze the user's query to extract necessary parameters for the chosen tool(s). "
        "If critical information for a tool is missing (e.g., a wallet address when no default is known), "
        "you MUST ask for clarification by calling the 'request_clarification' tool. Do not try to guess missing critical parameters. "
        "If a default wallet address is provided in the context, you may use it if the user doesn't specify one for a relevant tool."
    )
    
    # For Gemini, the prompt structure might be simpler if using `tools` directly.
    # Let's try passing the system instruction during model initialization or as part of the content.
    # The `tools` argument to `GenerativeModel` or `generate_content_async` handles the tool descriptions.

    prompt_parts = [system_instruction]
    if user_context:
        prompt_parts.append(f"\nUser Context: {json.dumps(user_context)}")
    prompt_parts.append(f"\nUser Query: {user_query}")
    
    final_prompt = "\n".join(prompt_parts)

    try:
        # Make the call to Gemini, providing the tools
        response = await _gemini_model.generate_content_async(
            final_prompt,
            tools=[SOLQUERY_TOOL_CONFIG] # Pass the defined tool configuration
        )
        
        actions_to_take = []
        # Check for function calls in the response
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    fc = part.function_call
                    actions_to_take.append({
                        "tool_name": fc.name,
                        "arguments": dict(fc.args) if fc.args else {}
                    })
        
        if actions_to_take:
            # If the LLM decided to call one or more of our functions
            return {"actions": actions_to_take}
        elif response.text:
            # If the LLM responded with text (e.g., a direct answer or asking for clarification without using a formal tool)
             # We could wrap this in a 'direct_answer' or try to interpret if it's a clarification
            if "clarification_needed" in response.text.lower() or "?" in response.text: # very basic check
                 return {"clarification_needed": response.text}
            return {"direct_answer": response.text}
        else:
            # No function call and no text, this is unusual
            return {"error": "LLM did not suggest an action or provide a text response."}

    except Exception as e:
        print(f"Error interacting with Gemini API for routing: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Gemini API routing error: {str(e)}"}


async def analyze_sentiment_with_llm(text_to_analyze: str, topic: Optional[str] = None) -> Dict[str, Any]:
    """
    Uses LLM to perform sentiment analysis.
    """
    configure_gemini_if_needed()
    if not _gemini_model or not _gemini_configured:
        return {"error": "Gemini API not configured for sentiment analysis."}

    topic_context = f"regarding '{topic}'" if topic else "regarding the provided text"
    prompt = f"""
    Analyze the sentiment of the following text {topic_context} from the Solana ecosystem.
    Classify the sentiment as 'Positive', 'Negative', or 'Neutral'.
    Provide a brief one-sentence justification for your classification.

    Text: "{text_to_analyze}"

    Respond ONLY with a JSON object with the keys "sentiment_classification" and "justification". Example:
    {{"sentiment_classification": "Positive", "justification": "The text expresses strong excitement about recent developments and price action."}}
    """
    try:
        response = await _gemini_model.generate_content_async(prompt) # No tools needed here
        
        # Attempt to parse the response text as JSON
        # Gemini might sometimes add markdown backticks around JSON, so strip them.
        response_text_cleaned = response.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        
        sentiment_data = json.loads(response_text_cleaned)
        return sentiment_data # Expected: {"sentiment_classification": "...", "justification": "..."}
    except json.JSONDecodeError:
        return {"error": "LLM returned non-JSON sentiment", "raw_response": response.text}
    except Exception as e:
        print(f"Error during sentiment analysis with Gemini: {e}")
        return {"error": f"Gemini API sentiment analysis error: {str(e)}", "raw_response": response.text if 'response' in locals() and hasattr(response, 'text') else "Unknown"}