import httpx
from ..core.config import settings
from typing import Dict, Any, Optional

# This will be our shared HTTP client.
# It's better to manage its lifecycle with FastAPI's lifespan events.
http_client: Optional[httpx.AsyncClient] = None
HELIUS_RPC_BASE_URL = "https://mainnet.helius-rpc.com/" # For mainnet-beta

# --- Mock Fukuoka Data ---
MOCK_FUKUOKA_COWORKING_SPACES = [
    {"id": "cw1", "name": "Fukuoka Creative Spark Hub", "category": "co-working space", "area": "Tenjin", "accepts_solana_payments": True, "details": "Popular with tech nomads, 20 USDC/day pass.", "rate_info": "20 USDC/day"},
    {"id": "cw2", "name": "Canal City Co-Work Central", "category": "co-working space", "area": "Hakata", "accepts_solana_payments": False, "details": "Modern facilities, near shopping.", "rate_info": "¥3000/day"},
    {"id": "cw3", "name": "Riverside Work & Cafe", "category": "co-working space", "area": "Nakasu", "accepts_solana_payments": True, "details": "Scenic views, also a cafe. Accepts SOL directly.", "rate_info": "Equivalent of ¥2500 in SOL/day"},
]
MOCK_FUKUOKA_RESTAURANTS = [
    {"id": "r1", "name": "Hakata Ramen Zen", "category": "restaurant", "area": "Hakata", "accepts_solana_payments": False, "details": "Famous for Tonkotsu ramen."},
    {"id": "r2", "name": "Tenjin Tempura Grill", "category": "restaurant", "area": "Tenjin", "accepts_solana_payments": True, "details": "Accepts USDC for meals over ¥5000."},
]
MOCK_FUKUOKA_EVENTS = [
    {"id": "ev1", "name": "Hakata Dontaku Port Festival", "date": "Next Weekend (May 17-18, 2025)", "description": "One of Fukuoka's largest festivals with parades and performances.", "accepts_crypto": False, "payment_info": "Tickets typically via standard vendors. Some street food stalls might accept mobile payments or cash; crypto unlikely for official tickets."},
    {"id": "ev2", "name": "Solana x Fukuoka Dev Meetup", "date": "May 20, 2025", "description": "Local developer meetup discussing Web3 and Solana.", "accepts_crypto": True, "payment_info": "Free entry, some merch might be available for SOL/USDC."},
]
MOCK_CRYPTO_PAYMENT_INFO = {
    "setting up phantom wallet": "To set up a Phantom wallet for Solana: 1. Download the Phantom extension for your browser or the mobile app from phantom.app. 2. Create a new wallet and securely save your secret recovery phrase. 3. You can then add SOL or SPL tokens like USDC.",
    "benefits of usdc for shops in fukuoka": "For shops in Fukuoka, accepting USDC on Solana means very low transaction fees (less than $0.01), near-instant settlement (seconds), and access to a global customer base of crypto users and digital nomads. It avoids traditional card fees.",
    "how to buy sol for a tourist": "As a tourist, you can buy SOL or USDC on Solana from major international crypto exchanges like Coinbase, Binance, or Kraken using your home currency/cards. Then, transfer it to your self-custody Solana wallet (e.g., Phantom) to use.",
    "solana pay": "Solana Pay is a specification that allows merchants to easily accept SOL or other Solana-based tokens like USDC directly from customer wallets, often via QR codes. It's fast, low-cost, and becoming more common."
}


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

async def get_sol_balance_service(wallet_address: str) -> Dict[str, Any]:
    """
    Fetches SOL balance for a given wallet address using Helius RPC.
    """
    if not http_client: await init_http_client()
    if "FALLBACK" in settings.HELIUS_API_KEY or not settings.HELIUS_API_KEY: 
        return {"error": "Helius API Key not configured"}
        
    rpc_url_with_key = f"{HELIUS_RPC_BASE_URL}?api-key={settings.HELIUS_API_KEY}"
    
    payload = {
        "jsonrpc": "2.0",
        "id": "SolQuery-GetSolBalance", 
        "method": "getBalance",
        "params": [wallet_address]
    }
    headers = {"Content-Type": "application/json"}
    print(f"DATA_SOURCES: Calling Helius getBalance for {wallet_address}")

    try:
        response = await http_client.post(rpc_url_with_key, json=payload, headers=headers)
        response.raise_for_status() 
        data = response.json()

        if data.get("error"):
            rpc_error = data["error"]
            error_msg = f"RPC Error: {rpc_error.get('message', 'Unknown JSON-RPC error')}"
            print(f"DATA_SOURCES: Error from getBalance: {error_msg}")
            return {"error": error_msg, "code": rpc_error.get("code", "N/A")}
        
        if "result" in data and isinstance(data["result"], dict) and "value" in data["result"]:
            return {
                "wallet": wallet_address, 
                "balance_lamports": data["result"]["value"],
                "source": "Helius RPC (getBalance)"
            }
        else:
            print(f"DATA_SOURCES: Unexpected response structure from getBalance: {data}")
            return {"error": "Unexpected response structure from Helius getBalance", "details": data}

    except httpx.HTTPStatusError as e:
        print(f"DATA_SOURCES: HTTP error calling getBalance: {e.response.status_code}, Response: {e.response.text}")
        return {"error": f"HTTP Error: {e.response.status_code}", "details": e.response.text}
    except httpx.RequestError as e:
        print(f"DATA_SOURCES: Request error calling getBalance: {str(e)}")
        return {"error": "Network request to Helius failed for getBalance", "details": str(e)}
    except Exception as e:
        print(f"DATA_SOURCES: Unexpected error in get_sol_balance_service: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": "An unexpected error occurred while fetching SOL balance", "details": str(e)}

async def get_spl_token_balances_service(wallet_address: str, page: int = 1, limit: int = 100) -> Dict[str, Any]:
    """
    Fetches SPL token balances for a given wallet address using Helius getAssetsByOwner.
    """
    if not http_client: await init_http_client()
    if "FALLBACK" in settings.HELIUS_API_KEY or not settings.HELIUS_API_KEY:
        return {"error": "Helius API Key not configured in .env"}

    rpc_url_with_key = f"{HELIUS_RPC_BASE_URL}?api-key={settings.HELIUS_API_KEY}"
    payload = {
        "jsonrpc": "2.0",
        "id": "SolQuery-GetSPLTokens",
        "method": "getAssetsByOwner",
        "params": {
            "ownerAddress": wallet_address,
            "page": page,
            "limit": limit,
            "options": { 
                "showFungible": True,
                "showNativeBalance": False, 
                "showCollectionMetadata": True, # May provide some token name/symbol data
                "showUnverifiedCollections": False 
            }
        }
    }
    headers = {"Content-Type": "application/json"}
    print(f"DATA_SOURCES: Fetching SPL token balances for {wallet_address} via getAssetsByOwner (page {page}, limit {limit})")

    try:
        response = await http_client.post(rpc_url_with_key, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data.get("error"):
            error_msg = f"RPC Error for SPL tokens: {data['error'].get('message', 'Unknown')}"
            print(f"DATA_SOURCES: {error_msg}")
            return {"error": error_msg, "code": data['error'].get('code', 'N/A')}

        if "result" in data and isinstance(data["result"], dict):
            result = data["result"]
            token_list = []
            for item in result.get("items", []):
                if item.get("interface") == "FungibleAsset" or item.get("interface", "").startswith("SPL") or item.get("token_info"):
                    token_info = item.get("token_info", {})
                    content_metadata = item.get("content", {}).get("metadata", {})
                    
                    mint_address = item.get("id")
                    balance = token_info.get("balance")
                    decimals = token_info.get("decimals")
                    
                    symbol = content_metadata.get("symbol") or token_info.get("symbol") # Prefer metadata if available
                    name = content_metadata.get("name") or token_info.get("name")
                    logo_uri = content_metadata.get("image") or content_metadata.get("logoURI") if content_metadata else None
                    price_usd = token_info.get("price_info", {}).get("price_per_token")

                    if mint_address and balance is not None and decimals is not None:
                        token_list.append({
                            "mint_address": mint_address, "symbol": symbol, "name": name,
                            "raw_amount": str(balance), "decimals": decimals,
                            "price_usd": price_usd, "logo_uri": logo_uri
                        })
            
            return {
                "wallet_address": wallet_address, "tokens": token_list,
                "total_on_page": len(token_list), "grand_total": result.get("total"),
                "page": result.get("page", page), "source": "Helius DAS API (Fungible)"
            }
        print(f"DATA_SOURCES: Unexpected response structure for SPLs from getAssetsByOwner: {data}")
        return {"error": "Unexpected response structure from Helius getAssetsByOwner for SPLs", "details": data}
    except httpx.HTTPStatusError as e:
        print(f"DATA_SOURCES: HTTP error fetching SPLs: {e.response.status_code}, Response: {e.response.text}")
        return {"error": f"HTTP Error: {e.response.status_code}", "details": e.response.text}
    except httpx.RequestError as e:
        print(f"DATA_SOURCES: Request error fetching SPLs: {str(e)}")
        return {"error": "Network request to Helius failed for SPLs", "details": str(e)}
    except Exception as e:
        print(f"DATA_SOURCES: Unexpected error in get_spl_token_balances_service: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": f"An unexpected error occurred while fetching SPL token balances: {str(e)}"}

async def get_spl_token_balances_service(wallet_address: str, page: int = 1, limit: int = 100) -> Dict[str, Any]:
    """
    Fetches SPL token balances for a given wallet address using Helius getAssetsByOwner.
    """
    if not http_client: await init_http_client()
    if "FALLBACK" in settings.HELIUS_API_KEY or not settings.HELIUS_API_KEY:
        return {"error": "Helius API Key not configured in .env"}

    rpc_url_with_key = f"{HELIUS_RPC_BASE_URL}?api-key={settings.HELIUS_API_KEY}"
    payload = {
        "jsonrpc": "2.0",
        "id": "SolQuery-GetSPLTokens",
        "method": "getAssetsByOwner",
        "params": {
            "ownerAddress": wallet_address,
            "page": page,
            "limit": limit,
            "displayOptions": { # Renamed from 'options' to 'displayOptions' as per some Helius DAS contexts
                "showFungible": True,        # IMPORTANT: Set to true for SPL tokens
                "showNativeBalance": False,  # We get SOL balance separately
                "showUnverifiedCollections": False, # Less relevant for fungibles but good to keep
                "showCollectionMetadata": False, # Less relevant for fungibles
                # For fungibles, metadata like name/symbol often comes from `content.metadata` or `token_info`
            }
        }
    }
    # Note: Helius docs for getAssetsByOwner refer to "displayOptions".
    # If "options" was correct for your version/specific endpoint, adjust as needed.
    # The example you provided used "options". I'll stick to "options" if that worked for NFTs.
    # Reverting to "options" based on your provided NFT example structure.
    payload["params"]["options"] = payload["params"].pop("displayOptions")
    payload["params"]["options"]["showCollectionMetadata"] = True # Try to get any metadata Helius attaches

    headers = {"Content-Type": "application/json"}
    print(f"DATA_SOURCES: Fetching SPL token balances for {wallet_address} using Helius getAssetsByOwner")

    try:
        response = await http_client.post(rpc_url_with_key, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data.get("error"):
            return {"error": f"RPC Error: {data['error'].get('message', 'Unknown JSON-RPC error')}", "code": data['error'].get('code', 'N/A')}

        if "result" in data and isinstance(data["result"], dict):
            result = data["result"]
            token_list = []
            for item in result.get("items", []):
                # We are interested in items with an interface like "FungibleToken", "SPL", or similar.
                # Helius DAS API might use "FungibleAsset" or specific SPL interfaces.
                # The key is that `token_info` field is usually present for fungibles.
                if item.get("interface") == "FungibleAsset" or item.get("interface", "").startswith("SPL") or item.get("token_info"): # Adjust interface check as needed
                    token_info = item.get("token_info", {})
                    content_metadata = item.get("content", {}).get("metadata", {})
                    
                    mint_address = item.get("id")
                    balance = token_info.get("balance")
                    decimals = token_info.get("decimals")
                    
                    # Helius might put symbol/name in content.metadata for fungibles too
                    symbol = content_metadata.get("symbol") if content_metadata else token_info.get("symbol")
                    name = content_metadata.get("name") if content_metadata else token_info.get("name")
                    logo_uri = content_metadata.get("image") or content_metadata.get("logoURI") if content_metadata else None


                    # Price info might be nested if Helius provides it
                    price_usd = token_info.get("price_info", {}).get("price_per_token")
                    # value_usd will be calculated in portfolio_service if price_usd is found/fetched

                    if mint_address and balance is not None and decimals is not None:
                        token_list.append({
                            "mint_address": mint_address,
                            "symbol": symbol,
                            "name": name,
                            "raw_amount": str(balance),
                            "decimals": decimals,
                            "price_usd": price_usd, # This might be None if not provided by Helius here
                            "logo_uri": logo_uri
                            # ui_amount and value_usd will be calculated in portfolio_service
                        })
            
            return {
                "wallet_address": wallet_address,
                "tokens": token_list,
                "total_on_page": len(token_list),
                "grand_total": result.get("total"), # Total items if displayOptions.showGrandTotal was true
                "page": result.get("page", page),
                "source": "Helius DAS API (getAssetsByOwner - Fungible)"
            }
        return {"error": "Unexpected response structure from Helius getAssetsByOwner for SPLs", "details": data}
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP Error: {e.response.status_code}", "details": e.response.text}
    except httpx.RequestError as e:
        return {"error": "Network request to Helius failed", "details": str(e)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"An unexpected error occurred while fetching SPL token balances: {str(e)}"}

async def get_spl_token_balances_service(wallet_address: str, page: int = 1, limit: int = 100) -> Dict[str, Any]:
    """
    Fetches SPL token balances for a given wallet address using Helius getAssetsByOwner.
    """
    if not http_client: await init_http_client() # Ensure http_client is initialized
    if "FALLBACK" in settings.HELIUS_API_KEY or not settings.HELIUS_API_KEY:
        return {"error": "Helius API Key not configured in .env"}

    rpc_url_with_key = f"{HELIUS_RPC_BASE_URL}?api-key={settings.HELIUS_API_KEY}"

    payload = {
        "jsonrpc": "2.0",
        "id": "SolQuery-GetSPLTokens",
        "method": "getAssetsByOwner",
        "params": {
            "ownerAddress": wallet_address,
            "page": page,
            "limit": limit,
            "options": { 
                "showFungible": True,        # IMPORTANT for SPL tokens
                "showNativeBalance": False,
                "showCollectionMetadata": True, # Might provide some token metadata
                "showUnverifiedCollections": False 
                # Add other options as needed from Helius docs for fungibles
            }
        }
    }
    headers = {"Content-Type": "application/json"}
    print(f"DATA_SOURCES: Fetching SPL token balances for {wallet_address} using Helius getAssetsByOwner")

    try:
        response = await http_client.post(rpc_url_with_key, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data.get("error"):
            # ... (error handling) ...
            return {"error": f"RPC Error for SPL tokens: {data['error'].get('message', 'Unknown')}"}

        if "result" in data and isinstance(data["result"], dict):
            # ... (parsing logic for SPL token items as detailed in the previous response) ...
            # Ensure you are extracting fields like id (mint), token_info.balance, 
            # token_info.decimals, content.metadata.name, content.metadata.symbol, etc.
            token_list = [] 
            for item in data["result"].get("items", []):
                if item.get("interface") == "FungibleAsset" or item.get("token_info"): # Adjust based on actual Helius response for SPLs
                    token_info = item.get("token_info", {})
                    content_metadata = item.get("content", {}).get("metadata", {})

                    mint_address = item.get("id")
                    balance = token_info.get("balance")
                    decimals = token_info.get("decimals")
                    symbol = content_metadata.get("symbol") if content_metadata else token_info.get("symbol")
                    name = content_metadata.get("name") if content_metadata else token_info.get("name")
                    logo_uri = content_metadata.get("image") or content_metadata.get("logoURI") if content_metadata else None
                    price_usd = token_info.get("price_info", {}).get("price_per_token")

                    if mint_address and balance is not None and decimals is not None:
                        token_list.append({
                            "mint_address": mint_address, "symbol": symbol, "name": name,
                            "raw_amount": str(balance), "decimals": decimals,
                            "price_usd": price_usd, "logo_uri": logo_uri
                        })
            return {
                "wallet_address": wallet_address, "tokens": token_list, 
                "total_on_page": len(token_list), "grand_total": data["result"].get("total"),
                "page": data["result"].get("page", page), "source": "Helius DAS API (Fungible)"
            }
        return {"error": "Unexpected response structure for SPLs", "details": data}
    # ... (except blocks as before) ...
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"An unexpected error occurred while fetching SPL token balances: {str(e)}"}


async def get_nft_holdings_service(wallet_address: str, limit: int = 50) -> Dict[str, Any]:
    # (Implementation using Helius getAssetsByOwner from previous response)
    if not http_client: await init_http_client()
    if "FALLBACK" in settings.HELIUS_API_KEY or not settings.HELIUS_API_KEY: return {"error": "Helius API Key not configured"}
    rpc_url_with_key = f"{HELIUS_RPC_BASE_URL}?api-key={settings.HELIUS_API_KEY}"
    payload = {
        "jsonrpc": "2.0", "id": "SolQuery-GetAssetsByOwner-NFTs", "method": "getAssetsByOwner",
        "params": {
            "ownerAddress": wallet_address, "page": 1, "limit": limit, # Simplified pagination for MVP
            "options": {"showFungible": False, "showCollectionMetadata": True, "showUnverifiedCollections": False}
        }
    }
    try:
        response = await http_client.post(rpc_url_with_key, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        data = response.json()
        if data.get("error"): return {"error": data["error"].get("message", "RPC error for NFTs")}
        if "result" in data and isinstance(data["result"], dict):
            items = data["result"].get("items", [])
            parsed_nfts = []
            for item in items:
                name = "Unknown NFT"
                if item.get("content") and item["content"].get("metadata"):
                    name = item["content"]["metadata"].get("name", name)
                collection_name = "Unknown Collection"
                collection_mint = None
                if item.get("grouping"):
                    for group in item["grouping"]:
                        if group.get("group_key") == "collection" and group.get("group_value"):
                            collection_mint = group["group_value"]
                            if group.get("collection_metadata") and group["collection_metadata"].get("name"):
                                collection_name = group["collection_metadata"]["name"]
                            break
                parsed_nfts.append({
                    "id": item.get("id"), "name": name, 
                    "image_uri": item.get("content", {}).get("files", [{}])[0].get("uri") if item.get("content", {}).get("files") else None,
                    "collection_name": collection_name, "collection_mint_id": collection_mint
                })
            return {"wallet_address": wallet_address, "nfts": parsed_nfts, "count": len(parsed_nfts)}
        return {"error": "Unexpected NFT response structure", "details": data}
    except Exception as e: return {"error": f"get_nfts_for_wallet failed: {str(e)}"}


async def find_fukuoka_local_services_service(category: str, accepts_solana_payments: Optional[bool] = None, area_in_fukuoka: Optional[str] = None) -> Dict[str, Any]:
    print(f"DATA_SOURCES: Searching Fukuoka services: Category='{category}', CryptoPay='{accepts_solana_payments}', Area='{area_in_fukuoka}'")
    results = []
    source_data = []
    if "co-working" in category.lower() or "coworking" in category.lower():
        source_data.extend(MOCK_FUKUOKA_COWORKING_SPACES)
    if "restaurant" in category.lower() or "cafe" in category.lower() or "food" in category.lower():
        source_data.extend(MOCK_FUKUOKA_RESTAURANTS)
        # Add cafes to restaurant mock or separate
    # Add more categories: shops, attractions etc.

    for item in source_data:
        area_match = True
        if area_in_fukuoka and area_in_fukuoka.lower() not in item.get("area", "").lower():
            area_match = False
        
        payment_match = True
        if accepts_solana_payments is not None and item.get("accepts_solana_payments") != accepts_solana_payments:
            payment_match = False
        
        if area_match and payment_match:
            results.append(item)
            
    return {"found_services": results if results else [{"message": "No matching services found with current mock data."}]}

async def get_fukuoka_events_service(timeframe: str, event_type: Optional[str] = None, accepts_crypto: Optional[bool] = None) -> Dict[str, Any]:
    print(f"DATA_SOURCES: Searching Fukuoka events: Timeframe='{timeframe}', Type='{event_type}', Crypto='{accepts_crypto}'")
    # MVP: Ignores timeframe and event_type for now, returns all mock events
    # TODO: Filter by timeframe and event_type
    results = MOCK_FUKUOKA_EVENTS
    if accepts_crypto is not None:
        results = [event for event in results if event.get("accepts_crypto") == accepts_crypto]
    return {"found_events": results if results else [{"message": "No matching events found with current mock data."}]}

async def get_crypto_payment_info_service(topic: str) -> Dict[str, Any]:
    print(f"DATA_SOURCES: Getting crypto payment info for topic: '{topic}'")
    for key_phrase, info in MOCK_CRYPTO_PAYMENT_INFO.items():
        if key_phrase in topic.lower():
            return {"topic": key_phrase, "information": info}
    return {"topic": topic, "information": "Sorry, I don't have specific information on that exact payment topic yet. Solana Pay with wallets like Phantom is generally fast and low-cost for SOL or USDC payments."}

async def get_text_for_sentiment_service(token_identifier: Optional[str] = None, nft_collection_name: Optional[str] = None) -> Dict[str, Any]:
    # (Using simplified mock text as before for MVP)
    target = token_identifier or nft_collection_name
    if not target: return {"error": "No target specified for sentiment text", "text": ""}
    print(f"DATA_SOURCES (MOCK): Fetching text for sentiment for {target}")
    if nft_collection_name:
         if nft_collection_name == "Mad Lads": return {"text": "Mad Lads are a top Solana collection, very hyped!", "topic": nft_collection_name}
         return {"text": f"General positive buzz around {nft_collection_name} NFTs.", "topic": nft_collection_name}
    if token_identifier:
        if token_identifier.upper() == "SOL": return {"text": "SOL is performing well, network upgrades are positive.", "topic": token_identifier}
        if token_identifier.upper() == "$JUP": return {"text": "JUP token has strong community backing and utility.", "topic": token_identifier}
        return {"text": f"Mixed news regarding {token_identifier}, some bullish some cautious.", "topic": token_identifier}
    return {"text": "No specific text found for sentiment analysis.", "topic": "Unknown"}