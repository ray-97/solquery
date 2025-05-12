import google.generativeai as genai
import os
from ..core.config import settings
from typing import Dict, Any, Optional

# Flag to ensure configuration happens only once
_gemini_configured = False

def configure_gemini_if_needed():
    global _gemini_configured
    if not _gemini_configured:
        if settings.GOOGLE_GEMINI_API_KEY and settings.GOOGLE_GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_FALLBACK":
            try:
                genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
                _gemini_configured = True
                print("Google Gemini API configured successfully.")
            except Exception as e:
                print(f"ERROR: Failed to configure Google Gemini API: {e}")
                # Potentially raise an error or handle appropriately
        else:
            print("WARNING: GOOGLE_GEMINI_API_KEY not found or is fallback. LLM service will not function.")

async def get_simple_gemini_response(prompt_text: str) -> Dict[str, Any]:
    """
    Sends a simple prompt to Gemini and returns the text response.
    """
    configure_gemini_if_needed()
    if not _gemini_configured:
        return {"error": "Gemini API not configured. Check API key."}

    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest') # Or your preferred model
        response = await model.generate_content_async(prompt_text)
        return {"response_text": response.text}
    except Exception as e:
        return {"error": f"Gemini API error: {str(e)}", "details": str(e)}

async def route_query_with_llm(user_query: str) -> Dict[str, Any]:
    """
    Uses LLM to understand user query intent for DeFi/NFT portfolio or sentiment.
    MVP: For now, just a passthrough or very simple logic.
    """
    configure_gemini_if_needed()
    if not _gemini_configured:
        return {"error": "Gemini API not configured for routing."}
    
    # For MVP, we might just echo or do a very basic classification
    # In a full version, this would involve a more complex prompt to extract intent and entities
    # prompt = f"Determine intent (e.g., GetPortfolio, GetSentiment) and entities for: '{user_query}'"
    # response = await model.generate_content_async(prompt)
    # parsed_intent_entities = parse_llm_response(response.text) # You'd need a parser
    
    print(f"LLM Routing (Placeholder): Received query '{user_query}'")
    if "balance" in user_query.lower():
        return {"intent": "get_balance", "entities": {"wallet_address_placeholder": "YOUR_WALLET_ADDRESS_HERE_FROM_QUERY_LATER"}}
    elif "nft" in user_query.lower():
        return {"intent": "get_nfts", "entities": {"wallet_address_placeholder": "YOUR_WALLET_ADDRESS_HERE_FROM_QUERY_LATER"}}
    elif "sentiment" in user_query.lower():
        return {"intent": "get_sentiment", "entities": {"topic_placeholder": "EXTRACT_TOPIC_LATER"}}
    
    # Fallback for MVP - just use Gemini to try and answer directly or rephrase
    simple_response = await get_simple_gemini_response(f"User asked about Solana: '{user_query}'. Provide a brief, helpful response or ask for clarification.")
    return {"intent": "general_query", "llm_direct_answer": simple_response.get("response_text")}


async def analyze_sentiment_with_llm(text_to_analyze: str) -> Dict[str, Any]:
    """
    Uses LLM to perform sentiment analysis.
    """
    configure_gemini_if_needed()
    if not _gemini_configured:
        return {"error": "Gemini API not configured for sentiment analysis."}

    prompt = f"""
    Analyze the sentiment of the following text regarding a Solana token or NFT project.
    Classify the sentiment as Positive, Negative, or Neutral, and provide a brief justification.

    Text: "{text_to_analyze}"

    Return a JSON object with "sentiment" and "justification". Example:
    {{"sentiment": "Positive", "justification": "The text expresses excitement about recent developments."}}
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = await model.generate_content_async(prompt)
        # In a real app, you'd parse response.text to a dict
        return {"sentiment_analysis_raw": response.text}
    except Exception as e:
        return {"error": f"Gemini API sentiment analysis error: {str(e)}"}