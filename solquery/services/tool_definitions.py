from google.generativeai.types import FunctionDeclaration, Tool

# --- Solana On-Chain Data Tools ---
GET_SOL_BALANCE = FunctionDeclaration(
    name="get_sol_balance",
    description="Fetches the current SOL (native Solana coin) balance for a given Solana wallet address.",
    parameters={  # Pass parameters as a dictionary
        "type": "object", # Use lowercase for type names
        "properties": {
            "wallet_address": {
                "type": "string",
                "description": "The public Solana wallet address (e.g., '3tA8PjUvrep7UT9LNWnHZQmQ5bg646YuZnt7xLiQAXEe')."
            }
        },
        "required": ["wallet_address"]
    }
)

GET_SPL_TOKEN_BALANCES = FunctionDeclaration(
    name="get_spl_token_balances",
    description="Fetches detailed balances for all SPL (fungible) tokens in a given Solana wallet, including their current market prices and total values if available.",
    parameters={
        "type": "object",
        "properties": {
            "wallet_address": {
                "type": "string",
                "description": "The public Solana wallet address."
            }
        },
        "required": ["wallet_address"]
    }
)

GET_NFT_HOLDINGS = FunctionDeclaration(
    name="get_nft_holdings",
    description="Lists all NFTs held in a given Solana wallet, often grouped by collection, including their names, image URIs, and collection identifiers. May include floor prices if available.",
    parameters={
        "type": "object",
        "properties": {
            "wallet_address": {
                "type": "string",
                "description": "The public Solana wallet address."
            },
            "limit": {
                "type": "integer", # Use 'integer' or 'number' based on JSON schema types
                "description": "Optional. Maximum number of NFTs to return. Defaults to 50."
            }
        },
        "required": ["wallet_address"] # 'limit' is optional
    }
)

# --- Fukuoka Specific Tools ---
FIND_FUKUOKA_LOCAL_SERVICES = FunctionDeclaration(
    name="find_fukuoka_local_services",
    description="Finds local services in Fukuoka, Japan, such as co-working spaces, restaurants, cafes, or artisan shops. Can filter by crypto payment acceptance (especially Solana or USDC) and specific areas within Fukuoka.",
    parameters={
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Type of service (e.g., 'co-working space', 'restaurant', 'cafe', 'tourist attraction', 'artisan shop')."
            },
            "accepts_solana_payments": {
                "type": "boolean",
                "description": "Optional. Filter for services that accept Solana-based payments (e.g., USDC on Solana, SOL). Set to true or false."
            },
            "area_in_fukuoka": {
                "type": "string",
                "description": "Optional. Specific area or district in Fukuoka (e.g., 'Tenjin', 'Hakata', 'Daimyo')."
            }
        },
        "required": ["category"]
    }
)

GET_FUKUOKA_EVENTS = FunctionDeclaration(
    name="get_fukuoka_events",
    description="Finds local events or festivals happening in Fukuoka within a given timeframe or that match certain criteria, including information about crypto payment acceptance if available.",
    parameters={
        "type": "object",
        "properties": {
            "timeframe": {
                "type": "string",
                "description": "The timeframe for events (e.g., 'this weekend', 'next month', 'today')."
            },
            "event_type": {
                "type": "string",
                "description": "Optional. Specific type of event (e.g., 'music festival', 'tech meetup', 'cultural event')."
            },
            "accepts_crypto": {
                "type": "boolean",
                "description": "Optional. Filter for events that might accept crypto payments or have crypto relevance."
            }
        },
        "required": ["timeframe"]
    }
)

GET_CRYPTO_PAYMENT_INFO = FunctionDeclaration(
    name="get_crypto_payment_info",
    description="Provides general information on how to use Solana (SOL, USDC) for payments, details on suitable wallets (like Phantom or Solflare), benefits for merchants, or where to acquire SOL/USDC. Specific to the context of Fukuoka or Japan if mentioned.",
    parameters={
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Specific question or topic about Solana payments (e.g., 'setting up a Phantom wallet', 'benefits of USDC for shops in Fukuoka', 'how to buy SOL for a tourist')."
            }
        },
        "required": ["topic"]
    }
)

# --- Sentiment Analysis Tools ---
GET_TEXT_FOR_SENTIMENT = FunctionDeclaration(
    name="get_text_for_sentiment",
    description="Fetches relevant recent text (news, discussions) about a specific Solana token or NFT collection that can then be used for sentiment analysis. Specify EITHER token_identifier OR nft_collection_name.",
    parameters={
        "type": "object",
        "properties": {
            "token_identifier": {
                "type": "string",
                "description": "The symbol or mint address of the SPL token (e.g., 'SOL', '$JUP'). Provide this OR nft_collection_name."
            },
            "nft_collection_name": {
                "type": "string",
                "description": "The name of the NFT collection (e.g., 'Mad Lads'). Provide this OR token_identifier."
            }
        }
        # 'required' field is omitted here, making both parameters effectively optional.
        # The LLM and your backend logic will need to ensure at least one is provided if necessary for the tool's function.
        # Or, make it: required: [] if none are truly required at the schema level for this specific tool.
        # Better: define two separate tools if the logic differs significantly or if one of them is always required.
        # For now, let's leave 'required' out, implying the LLM should fill one if relevant.
    }
)

ANALYZE_TEXT_SENTIMENT = FunctionDeclaration(
    name="analyze_text_sentiment",
    description="Analyzes the sentiment of a provided text string about a Solana project, token, or NFT collection. Returns Positive, Negative, or Neutral sentiment with a justification. This tool requires the text to be provided; it doesn't fetch the text itself.",
    parameters={
        "type": "object",
        "properties": {
            "text_to_analyze": {
                "type": "string",
                "description": "The text content (e.g., news article snippet, social media post summary) for which sentiment needs to be analyzed."
            },
            "topic": {
                "type": "string",
                "description": "The specific Solana project, token, or NFT collection the text is about. Helps focus the sentiment."
            }
        },
        "required": ["text_to_analyze", "topic"]
    }
)

# --- Tool object that groups all function declarations ---
SOLQUERY_TOOL_CONFIG = Tool(
    function_declarations=[
        GET_SOL_BALANCE,
        GET_SPL_TOKEN_BALANCES,
        GET_NFT_HOLDINGS,
        FIND_FUKUOKA_LOCAL_SERVICES,
        GET_FUKUOKA_EVENTS,
        GET_CRYPTO_PAYMENT_INFO,
        GET_TEXT_FOR_SENTIMENT,
        ANALYZE_TEXT_SENTIMENT,
    ]
)