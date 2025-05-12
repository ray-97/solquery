# solquery/services/data_sources.py
import httpx
from ..core.config import settings # To access API keys

# Initialize a single client for reuse (good practice)
# You might want to move this to main.py's startup/shutdown events
# or manage it within a dependency injection system for larger apps.
_http_client = None

async def get_http_client():
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient()
    return _http_client

async def close_http_client():
    global _http_client
    if _http_client:
        await _http_client.aclose()
        _http_client = None

async def get_sol_balance(wallet_address: str):
    client = await get_http_client()
    # This is a conceptual example for Helius RPC; refer to their actual docs
    # For Helius, you'd use your RPC URL which includes your API key
    # e.g., f"https://mainnet.helius-rpc.com/?api-key={settings.HELIUS_API_KEY}"
    rpc_url = f"https://your-helius-rpc-endpoint-with-api-key" # REPLACE THIS
    if "your-helius-rpc-endpoint" in rpc_url: # Reminder to replace
         print("WARNING: Replace with your actual Helius RPC endpoint in data_sources.py")
         return {"error": "Helius RPC endpoint not configured"}

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [wallet_address],
    }
    try:
        response = await client.post(rpc_url, json=payload)
        response.raise_for_status() # Raise an exception for bad status codes
        data = response.json()
        if "result" in data and "value" in data["result"]:
            return {"wallet": wallet_address, "balance_lamports": data["result"]["value"]}
        return {"error": data.get("error", "Unknown error from RPC")}
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error: {e.response.status_code} - {e.response.text}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}

# Add more functions later for fetching NFT data, DeFi positions, etc.