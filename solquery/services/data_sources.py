import httpx
from ..core.config import settings
from typing import Dict, Any, Optional

# This will be our shared HTTP client.
# It's better to manage its lifecycle with FastAPI's lifespan events.
http_client: Optional[httpx.AsyncClient] = None
HELIUS_RPC_BASE_URL = "https://mainnet.helius-rpc.com/" # For mainnet-beta

async def init_http_client():
    """To be called at application startup."""
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient()

async def close_http_client():
    """To be called at application shutdown."""
    global http_client
    if http_client:
        await http_client.aclose()
        http_client = None

async def get_sol_balance(wallet_address: str) -> Dict[str, Any]:
    """
    Fetches SOL balance for a given wallet address using Helius RPC.
    """
    if not http_client:
        # This path should ideally not be hit if lifespan events are working.
        print("WARNING: HTTP client was not initialized, initializing now.")
        await init_http_client()
        if not http_client: # Still None after trying to init
            return {"error": "HTTP client could not be initialized"}

    if "YOUR_HELIUS_API_KEY_FALLBACK" in settings.HELIUS_API_KEY or not settings.HELIUS_API_KEY:
        print("WARNING: Helius API Key not properly configured in .env. Cannot fetch balance.")
        return {"error": "Helius API Key not configured"}

    # Construct the full RPC URL with the API key
    # Ensure HELIUS_API_KEY in your .env is JUST the key, not the full URL.
    rpc_url_with_key = f"{HELIUS_RPC_BASE_URL}?api-key={settings.HELIUS_API_KEY}"
    
    # According to Solana RPC docs for getBalance, params is an array:
    # [String (Pubkey), GetBalanceConfigObject? (Optional)]
    # We'll use the simple version: [String (Pubkey)]
    payload = {
        "jsonrpc": "2.0",
        "id": "1", # You can use a unique ID generator if needed, but "1" is fine for simple cases
        "method": "getBalance",
        "params": [wallet_address]
    }
    headers = {
        "Content-Type": "application/json"
    }

    print(f"DEBUG: Calling Helius getBalance for {wallet_address} at {HELIUS_RPC_BASE_URL} (key hidden)") # Don't log the full key URL

    try:
        response = await http_client.post(rpc_url_with_key, json=payload, headers=headers)
        
        # Check for HTTP errors first (like 401 Unauthorized, 403 Forbidden, 429 Rate Limit, 5xx Server Errors)
        response.raise_for_status() 
        
        data = response.json() # If raise_for_status didn't trigger, we have a 2xx response

        # Now check for JSON-RPC level errors within the 2xx response
        if data.get("error"):
            rpc_error = data["error"]
            error_message = rpc_error.get("message", "Unknown JSON-RPC error")
            error_code = rpc_error.get("code", "N/A")
            print(f"ERROR: JSON-RPC error from Helius: Code {error_code}, Msg: {error_message}, Details: {rpc_error}")
            return {"error": f"RPC Error: {error_message}", "code": error_code, "details": rpc_error}

        if "result" in data and isinstance(data["result"], dict) and "value" in data["result"]:
            # The 'value' for getBalance is the balance in lamports (integer)
            return {
                "wallet": wallet_address,
                "balance_lamports": data["result"]["value"],
                "source": "Helius RPC"
            }
        else:
            # This case handles unexpected successful response structures.
            print(f"ERROR: Unexpected successful response structure from Helius: {data}")
            return {"error": "Unexpected response structure from Helius getBalance", "details": data}

    except httpx.HTTPStatusError as e:
        # Handles 4xx/5xx HTTP errors
        error_body = e.response.text
        try:
            error_json = e.response.json() # Try to parse if it's JSON
            error_details = error_json.get("error", error_body)
        except ValueError: # Not JSON
            error_details = error_body
        print(f"ERROR: HTTP error calling Helius: {e.response.status_code}, Response: {error_details}")
        return {"error": f"HTTP Error: {e.response.status_code}", "details": error_details}
    except httpx.RequestError as e:
        # Handles network errors, timeouts, etc.
        print(f"ERROR: Request error calling Helius: {str(e)}")
        return {"error": "Network request to Helius failed", "details": str(e)}
    except Exception as e:
        # Catch-all for other unexpected errors during the process
        print(f"ERROR: Unexpected error in get_sol_balance: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": "An unexpected error occurred while fetching SOL balance", "details": str(e)}

async def get_nfts_for_wallet(
    wallet_address: str, 
    page: int = 1, 
    limit: int = 50 # Helius default is 1000, max is 1000. Let's use a smaller default for MVP.
) -> Dict[str, Any]:
    """
    Fetches NFTs for a given wallet address using Helius getAssetsByOwner.
    (Assumes HELIUS_API_KEY in .env is just the key string)
    """
    if not http_client:
        await init_http_client()
        if not http_client: return {"error": "HTTP client could not be initialized"}

    if "YOUR_HELIUS_API_KEY_FALLBACK" in settings.HELIUS_API_KEY or not settings.HELIUS_API_KEY:
        return {"error": "Helius API Key not configured in .env"}

    rpc_url_with_key = f"{HELIUS_RPC_BASE_URL}?api-key={settings.HELIUS_API_KEY}"

    payload = {
        "jsonrpc": "2.0",
        "id": "SolQuery-GetAssetsByOwner", # Unique ID for the request
        "method": "getAssetsByOwner",
        "params": {
            "ownerAddress": wallet_address,
            "page": page,
            "limit": limit,
            "sortBy": {"sortBy": "created", "sortDirection": "asc"}, # Optional: or "recent_action", "none"
            "options": { # These options help filter and shape the response
                "showUnverifiedCollections": False,
                "showCollectionMetadata": True, # Set to True to get collection name if available directly
                "showFungible": False,          # We only want NFTs
                "showNativeBalance": False,
                "showInscription": False,       # Assuming we don't need inscription data for now
                "showZeroBalance": False
            }
        }
    }
    headers = {"Content-Type": "application/json"}
    # print(f"DEBUG: Calling Helius getAssetsByOwner for {wallet_address}, page {page}, limit {limit}")

    try:
        response = await http_client.post(rpc_url_with_key, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data.get("error"):
            rpc_error = data["error"]
            return {"error": f"RPC Error: {rpc_error.get('message', 'Unknown JSON-RPC error')}", "code": rpc_error.get("code", "N/A")}

        if "result" in data and isinstance(data["result"], dict):
            result = data["result"]
            parsed_nfts = []
            for item in result.get("items", []):
                nft_details = {"id": item.get("id")} # This is the mint address of the NFT

                # Extract content details (metadata URI, image)
                if item.get("content"):
                    content = item["content"]
                    nft_details["json_uri"] = content.get("json_uri")
                    # Attempt to get a name from metadata if Helius provides it directly
                    # Helius's getAssetsByOwner with showCollectionMetadata might add a 'name' in 'content.metadata'
                    # or within the collection grouping. The provided sample doesn't show this expanded.
                    # For MVP, we'll rely on what's directly available or the json_uri.
                    if content.get("metadata") and isinstance(content["metadata"], dict):
                         nft_details["name"] = content["metadata"].get("name")
                    
                    if content.get("files") and isinstance(content["files"], list) and len(content["files"]) > 0:
                        nft_details["image_uri"] = content["files"][0].get("uri")
                        nft_details["cdn_image_uri"] = content["files"][0].get("cdn_uri") # Helius provides CDN link

                # Extract collection information
                if item.get("grouping") and isinstance(item["grouping"], list):
                    for group in item["grouping"]:
                        if group.get("group_key") == "collection":
                            nft_details["collection_mint_id"] = group.get("group_value")
                            # If showCollectionMetadata was true, Helius might inject collection name here too
                            # e.g., in group.get("collection_metadata", {}).get("name")
                            if group.get("collection_metadata") and isinstance(group["collection_metadata"], dict):
                                nft_details["collection_name"] = group["collection_metadata"].get("name")
                            break 
                
                # If name still not found and json_uri exists, LLM could fetch/parse later or we can do it here
                if not nft_details.get("name") and nft_details.get("json_uri"):
                    # For MVP, we might just note the json_uri. A further step would be to fetch and parse this URI.
                    nft_details["name"] = f"Name to be fetched from json_uri"


                parsed_nfts.append(nft_details)
            
            return {
                "wallet": wallet_address,
                "total_nfts_on_page": len(parsed_nfts),
                "total_possible_nfts_for_wallet": result.get("total"), # Total items matching query if showGrandTotal was true
                "page": result.get("page", page),
                "limit": result.get("limit", limit),
                "nfts": parsed_nfts,
                "source": "Helius DAS API (getAssetsByOwner)"
            }
        
        return {"error": "Unexpected response structure from Helius getAssetsByOwner", "details": data}
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP Error: {e.response.status_code}", "details": e.response.text}
    except httpx.RequestError as e:
        return {"error": "Network request to Helius failed", "details": str(e)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": "An unexpected error occurred while fetching NFTs", "details": str(e)}

MOCK_NFT_TEXT_DATA = {
    "Mad Lads": "Recent announcements about Mad Lads partnerships have generated significant buzz, with many collectors expressing bullish sentiment. The floor price has seen a 15% increase this week.",
    "Tensorians": "While Tensorians remain a blue-chip collection, some community members are concerned about the lack of recent roadmap updates. Trading volume has been flat.",
    # Add 1-2 more examples
}

MOCK_TOKEN_TEXT_DATA = {
    "SOL": "Solana (SOL) is experiencing high network activity and positive developer sentiment following the latest network upgrade. Price predictions are generally optimistic for the quarter.",
    "JUP": "Jupiter (JUP) token saw a surge in trading volume after the announcement of its new governance proposal, though some are wary of its short-term volatility.",
    # Add 1-2 more examples
}

async def get_text_for_sentiment_analysis_nft(collection_name: str) -> Dict[str, Any]:
    print(f"Fetching MOCK text for sentiment analysis for NFT Collection: {collection_name}")
    text = MOCK_NFT_TEXT_DATA.get(collection_name, 
                                 f"No specific mock text found for {collection_name}. General sentiment appears stable.")
    return {"text": text, "source": "Mock Data"}

async def get_text_for_sentiment_analysis_token(token_id: str) -> Dict[str, Any]:
    # Normalize token_id if it has '$'
    normalized_token_id = token_id.upper().replace('$', '')
    print(f"Fetching MOCK text for sentiment analysis for Token: {normalized_token_id}")
    text = MOCK_TOKEN_TEXT_DATA.get(normalized_token_id,
                                    f"No specific mock text found for {normalized_token_id}. Market conditions seem mixed.")
    return {"text": text, "source": "Mock Data"}