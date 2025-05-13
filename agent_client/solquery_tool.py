# solquery_tool.py

import httpx
from typing import Type, Optional, Any
from pydantic import BaseModel, Field

from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun

# Define the input schema for the tool, though it's just a string for now
class SolQueryInput(BaseModel):
    query_text: str = Field(description="The natural language query about Solana DeFi, NFTs, portfolio, or sentiment.")

class SolQueryTool(BaseTool):
    name: str = "solana_query_engine"
    description: str = (
        "Use this tool to answer questions about the Solana blockchain. "
        "It is specialized in DeFi (Decentralized Finance) positions, NFT (Non-Fungible Token) details and collections, "
        "wallet portfolio summaries (token balances, NFT counts), transaction history, "
        "and sentiment analysis concerning Solana tokens and NFT collections. "
        "Input should be a clear, natural language question. For example: 'What is the floor price of Mad Lads NFTs?' or 'Show my SOL balance and recent transactions for wallet X.' or 'What's the current sentiment for $JUP?'"
        "For each question, only ask for one type of information at a time. "
        "For example, if you want to know about your NFTs and your SOL balance, ask them in two separate questions. "
    )
    args_schema: Type[BaseModel] = SolQueryInput
    solquery_api_url: str = "http://127.0.0.1:8000/query"  # Make this configurable if needed

    # Use _run for synchronous version if preferred, but _arun is better for FastAPI
    def _run(
        self, query_text: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool synchronously."""
        # This is a simplified synchronous wrapper if needed.
        # For a truly synchronous version, httpx.Client would be used.
        # However, it's often better to make the agent fully async if the tool is async.
        # For now, let's raise a NotImplementedError or implement with httpx.Client
        # raise NotImplementedError("SolQueryTool does not support synchronous run, use arun instead.")
        try:
            with httpx.Client() as client:
                payload = {"query_text": query_text}
                response = client.post(self.solquery_api_url, json=payload, timeout=60.0) # Increased timeout
                response.raise_for_status() # Raise an exception for bad status codes
                result = response.json()
                
                if result.get("success"):
                    answer = result.get("answer")
                    if isinstance(answer, dict):
                        # Simple string representation for now.
                        # You might want to format this more nicely or allow the LLM to summarize it.
                        return str(answer) 
                    return str(answer) if answer is not None else "No answer found."
                else:
                    error_message = result.get("error", {}).get("message", "Unknown error from SolQuery")
                    return f"Error from SolQuery: {error_message}"
        except httpx.HTTPStatusError as e:
            return f"HTTP error calling SolQuery: {e.response.status_code} - {e.response.text}"
        except httpx.RequestError as e:
            return f"Request error calling SolQuery: {str(e)}"
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"

    async def _arun(
        self, query_text: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool asynchronously."""
        async with httpx.AsyncClient() as client:
            payload = {"query_text": query_text}
            try:
                response = await client.post(self.solquery_api_url, json=payload, timeout=60.0) # Increased timeout
                response.raise_for_status() # Raise an exception for bad status codes
                result = response.json()

                if result.get("success"):
                    answer = result.get("answer")
                    # The agent expects a string. If SolQuery returns complex JSON,
                    # you might want the LLM to summarize this, or your tool can format it.
                    # For now, let's convert dicts to a string representation.
                    if isinstance(answer, dict):
                        # Convert dict to a somewhat readable string.
                        # You might want a more sophisticated summarization step here,
                        # potentially involving another LLM call if the data is very complex.
                        return ", ".join([f"{key}: {value}" for key, value in answer.items()])
                    return str(answer) if answer is not None else "No answer found from SolQuery."
                else:
                    error_message = result.get("error", {}).get("message", "Unknown error from SolQuery API.")
                    return f"Error from SolQuery: {error_message}"
            except httpx.HTTPStatusError as e:
                return f"HTTP error connecting to SolQuery API: {e.response.status_code} - {e.response.text}"
            except httpx.RequestError as e:
                # This catches network errors, timeouts (if not httpx.ReadTimeout specifically), etc.
                return f"Error connecting to SolQuery API: {str(e)}"
            except Exception as e:
                return f"An unexpected error occurred while calling SolQuery: {str(e)}"