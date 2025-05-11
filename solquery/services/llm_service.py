import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API key
gemini_api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

if not gemini_api_key:
    raise ValueError("GOOGLE_GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")

genai.configure(api_key=gemini_api_key)

# Now you can create a model instance, for example:
# model = genai.GenerativeModel('gemini-1.5-flash-latest') # Or other appropriate Gemini model
# response = model.generate_content("Your prompt here")
# print(response.text)

# --- Your llm_service.py functions will go here ---

async def route_query_with_gemini(user_query: str):
    # Example of how you might use Gemini for routing or understanding a query
    model = genai.GenerativeModel('gemini-1.5-flash-latest') # Or your preferred model for this task
    
    prompt = f"""
    Analyze the following user query related to Solana DeFi or NFTs and determine the primary intent 
    and key entities. The user wants to manage their portfolio or get sentiment analysis.

    User Query: "{user_query}"

    Possible Intents: GetPortfolioValue, GetDeFiPositions, GetNFTs, GetTokenSentiment, GetCollectionSentiment, GetTransactionHistory.
    Key Entities: WalletAddress, TokenSymbol, NFTCollectionName, TimePeriod.

    Return a JSON object with "intent" and "entities". For example:
    {{"intent": "GetPortfolioValue", "entities": {{"WalletAddress": "YourWalletAddressHere"}}}}
    {{"intent": "GetTokenSentiment", "entities": {{"TokenSymbol": "SOL"}}}}
    """
    
    try:
        response = await model.generate_content_async(prompt) # Use async for FastAPI
        # Process response.text, which might be a JSON string, or use structured output if supported
        # Be sure to handle potential errors in LLM response or parsing
        return response.text 
    except Exception as e:
        print(f"Error interacting with Gemini API: {e}")
        return None # Or raise a specific exception

async def analyze_sentiment_with_gemini(text_to_analyze: str):
    model = genai.GenerativeModel('gemini-1.5-flash-latest') # Or a model fine-tuned for sentiment
    
    prompt = f"""
    Analyze the sentiment of the following text regarding a Solana token or NFT project. 
    Classify the sentiment as Positive, Negative, or Neutral, and provide a brief justification.

    Text: "{text_to_analyze}"

    Return a JSON object with "sentiment" and "justification". For example:
    {{"sentiment": "Positive", "justification": "The text expresses excitement about recent developments."}}
    """
    try:
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        print(f"Error interacting with Gemini API for sentiment analysis: {e}")
        return None