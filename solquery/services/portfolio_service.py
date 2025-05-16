# solquery/services/portfolio_service.py
from typing import Dict, Any, List, Optional
from . import data_sources
from ..schemas.defi_schemas import DeFiPortfolio, NativeBalance, TokenHolding
from ..schemas.nft_schemas import NFTPortfolio, NFTHolding
import asyncio

# Example placeholder for fetching multiple token prices if not provided by Helius
# In a real app, use a batch-capable price API like CoinGecko's /simple/token_price
MOCK_TOKEN_PRICES_USD = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": 1.00,  # USDC
    "JUPyiwrYJFskUPiK7EPk3rR7fnfPpzpbadgWvWzTBPH": 0.85,   # JUP
    "So11111111111111111111111111111111111111112": 150.00, # WSOL (should match SOL price)
    # Add other common tokens you might encounter in test wallets
}

async def get_sol_price_usd_service() -> float:
    # TODO: Integrate a real price feed (e.g., via data_sources.py using CoinGecko for SOL)
    # For now, using the mock price also used for WSOL
    return MOCK_TOKEN_PRICES_USD.get("So11111111111111111111111111111111111111112", 150.0)

class PortfolioService:
    async def get_full_defi_portfolio(self, wallet_address: str) -> DeFiPortfolio:
        errors = []
        
        sol_balance_data_task = data_sources.get_sol_balance_service(wallet_address)
        spl_tokens_data_task = data_sources.get_spl_token_balances_service(wallet_address) # This now calls Helius

        sol_balance_data, spl_tokens_helius_data = await asyncio.gather(
            sol_balance_data_task,
            spl_tokens_data_task
        )
        
        sol_price = await get_sol_price_usd_service()
        native_balance_obj = NativeBalance(ui_amount=0, raw_amount="0", price_usd=sol_price, value_usd=0) 
        if not sol_balance_data.get("error") and "balance_lamports" in sol_balance_data:
            lamports_per_sol = 1_000_000_000
            ui_amount = sol_balance_data["balance_lamports"] / lamports_per_sol
            native_balance_obj = NativeBalance(
                ui_amount=ui_amount,
                raw_amount=str(sol_balance_data["balance_lamports"]),
                price_usd=sol_price,
                value_usd=ui_amount * sol_price
            )
        elif sol_balance_data.get("error"):
             errors.append(f"SOL Balance Error: {sol_balance_data['error']}")

        token_holdings_list: List[TokenHolding] = []
        total_spl_value_usd = 0.0
        if not spl_tokens_helius_data.get("error") and "tokens" in spl_tokens_helius_data:
            for token_data_from_helius in spl_tokens_helius_data.get("tokens", []):
                price_usd = token_data_from_helius.get("price_usd") 
                if price_usd is None: # If Helius didn't provide price
                    # Try to get from our mock/cached prices or call a price API
                    price_usd = MOCK_TOKEN_PRICES_USD.get(token_data_from_helius["mint_address"])
                    # TODO: If still None, call CoinGecko or other price API here for token_data_from_helius["mint_address"]
                    if price_usd is None:
                        print(f"Warning: Price not found for token {token_data_from_helius.get('symbol') or token_data_from_helius['mint_address']}")

                ui_amount_val = None
                value_usd_val = None
                if token_data_from_helius.get("decimals") is not None and token_data_from_helius.get("raw_amount") is not None:
                    ui_amount_val = int(token_data_from_helius["raw_amount"]) / (10**token_data_from_helius["decimals"])
                    if price_usd is not None:
                        value_usd_val = ui_amount_val * price_usd
                        total_spl_value_usd += value_usd_val
                
                token_holdings_list.append(TokenHolding(
                    mint_address=token_data_from_helius["mint_address"],
                    symbol=token_data_from_helius.get("symbol"),
                    name=token_data_from_helius.get("name"),
                    ui_amount=ui_amount_val,
                    raw_amount=token_data_from_helius["raw_amount"],
                    decimals=token_data_from_helius["decimals"],
                    price_usd=price_usd,
                    value_usd=value_usd_val,
                    logo_uri=token_data_from_helius.get("logo_uri")
                ))
        elif spl_tokens_helius_data.get("error"):
            errors.append(f"SPL Token Error: {spl_tokens_helius_data['error']}")
            
        # TODO: Populate an 'errors' field in DeFiPortfolio if desired.
        # For now, errors are just printed or would be caught by main.py if exceptions were raised.

        return DeFiPortfolio(
            wallet_address=wallet_address,
            sol_balance=native_balance_obj,
            token_holdings=token_holdings_list,
            total_spl_tokens_value_usd=total_spl_value_usd if token_holdings_list else 0.0
        )

    async def get_nft_portfolio_details(self, wallet_address: str, limit: int = 50) -> NFTPortfolio:
        # This function can remain largely the same as before, as get_nft_holdings_service already parses Helius output
        nft_data_dict = await data_sources.get_nft_holdings_service(wallet_address, limit=limit)
        
        nft_holdings_list: List[NFTHolding] = []
        errors = [] # For collecting errors

        if nft_data_dict.get("error"):
            errors.append(f"NFT Holdings Error: {nft_data_dict['error']}")
        elif "nfts" in nft_data_dict:
            for nft_item_data in nft_data_dict.get("nfts", []):
                # TODO: Fetch actual floor price for collection_mint_id
                # For MVP, floor_price_usd can be None.
                nft_holdings_list.append(NFTHolding(
                    id=nft_item_data.get("id"), 
                    name=nft_item_data.get("name", "N/A"),
                    image_uri=nft_item_data.get("image_uri"),
                    cdn_image_uri=nft_item_data.get("cdn_image_uri"),
                    json_uri=nft_item_data.get("json_uri"),
                    collection_mint_id=nft_item_data.get("collection_mint_id"),
                    collection_name=nft_item_data.get("collection_name", "Unknown Collection"),
                    floor_price_usd=None # Placeholder
                ))
        
        # TODO: Add error reporting to NFTPortfolio schema if needed
        return NFTPortfolio(
            wallet_address=wallet_address,
            nft_holdings=nft_holdings_list,
            total_nfts_count=len(nft_holdings_list)
        )

portfolio_service_instance = PortfolioService()