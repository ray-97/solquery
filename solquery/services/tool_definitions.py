# solquery/services/tool_definitions.py
from google.generativeai.types import HarmCategory, HarmBlockThreshold, FunctionDeclaration, Tool

# Define the functions (tools) that SolQuery can execute.
# These declarations will be passed to the Gemini model.

GET_WALLET_PORTFOLIO_SUMMARY = FunctionDeclaration(
    name="get_wallet_portfolio_summary",
    description="Fetches a summary of a Solana wallet's portfolio, including SOL balance, count of SPL tokens, and count of NFTs. Use this for general overview requests about a wallet's holdings.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "wallet_address": {
                "type": "STRING",
                "description": "The public Solana wallet address (e.g., '3tA8PjUvrep7UT9LNWnHZQmQ5bg646YuZnt7xLiQAXEe')."
            }
        },
        "required": ["wallet_address"]
    }
)

GET_DETAILED_SPL_TOKEN_BALANCES = FunctionDeclaration(
    name="get_detailed_spl_token_balances",
    description="Fetches detailed balances for all SPL (fungible) tokens in a given Solana wallet, including their current market prices and total values, if available.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "wallet_address": {
                "type": "STRING",
                "description": "The public Solana wallet address."
            }
        },
        "required": ["wallet_address"]
    }
)

GET_WALLET_NFT_COLLECTION = FunctionDeclaration(
    name="get_wallet_nft_collection",
    description="Lists all NFTs held in a given Solana wallet, often grouped by collection, including their names and identifiers. May include floor prices if available.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "wallet_address": {
                "type": "STRING",
                "description": "The public Solana wallet address."
            }
        },
        "required": ["wallet_address"]
    }
)

GET_NFT_COLLECTION_SENTIMENT = FunctionDeclaration(
    name="get_nft_collection_sentiment",
    description="Analyzes and returns the current market sentiment (Positive, Negative, Neutral) for a specific NFT collection on Solana based on recent news and social media discussions. Also provides a brief justification.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "collection_name": {
                "type": "STRING",
                "description": "The name of the NFT collection (e.g., 'Mad Lads', 'Tensorians')."
            }
        },
        "required": ["collection_name"]
    }
)

GET_TOKEN_SENTIMENT = FunctionDeclaration(
    name="get_token_sentiment",
    description="Analyzes and returns the current market sentiment (Positive, Negative, Neutral) for a specific Solana SPL token (e.g., SOL, JUP, PYTH) based on recent news and social media discussions. Also provides a brief justification.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "token_symbol_or_mint_address": {
                "type": "STRING",
                "description": "The symbol (e.g., 'SOL', '$JUP') or the mint address of the SPL token."
            }
        },
        "required": ["token_symbol_or_mint_address"]
    }
)

GET_TRANSACTION_HISTORY = FunctionDeclaration(
    name="get_transaction_history",
    description="Fetches the recent transaction history for a given Solana wallet address, possibly focusing on DeFi and NFT activities.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "wallet_address": {
                "type": "STRING",
                "description": "The public Solana wallet address."
            },
            "limit": {
                "type": "INTEGER",
                "description": "Optional. Number of recent transactions to fetch. Defaults to 10 if not specified."
            }
        },
        "required": ["wallet_address"]
    }
)

# Tool object that groups all function declarations
SOLQUERY_TOOL_CONFIG = Tool(
    function_declarations=[
        GET_WALLET_PORTFOLIO_SUMMARY,
        GET_DETAILED_SPL_TOKEN_BALANCES,
        GET_WALLET_NFT_COLLECTION,
        GET_NFT_COLLECTION_SENTIMENT,
        GET_TOKEN_SENTIMENT,
        GET_TRANSACTION_HISTORY,
        # Add other function declarations here as you create more services
    ]
)

# It can also be useful to have a map of tool names to their parameter requirements for validation
TOOL_PARAMETER_SCHEMAS = {
    "get_wallet_portfolio_summary": GET_WALLET_PORTFOLIO_SUMMARY.parameters,
    "get_detailed_spl_token_balances": GET_DETAILED_SPL_TOKEN_BALANCES.parameters,
    "get_wallet_nft_collection": GET_WALLET_NFT_COLLECTION.parameters,
    "get_nft_collection_sentiment": GET_NFT_COLLECTION_SENTIMENT.parameters,
    "get_token_sentiment": GET_TOKEN_SENTIMENT.parameters,
    "get_transaction_history": GET_TRANSACTION_HISTORY.parameters,
}