from pydantic import BaseModel, Field
from typing import List, Optional

class TokenHolding(BaseModel):
    mint_address: str = Field(..., description="The mint address of the SPL token.")
    symbol: Optional[str] = Field(None, description="The token's symbol (e.g., JUP, USDC).")
    name: Optional[str] = Field(None, description="The token's name (e.g., Jupiter, USD Coin).")
    ui_amount: Optional[float] = Field(None, description="The token balance in human-readable format (decimal adjusted).")
    raw_amount: str = Field(..., description="The raw token balance as a string (lamports or smallest unit).")
    decimals: int = Field(..., description="The token's decimals.")
    price_usd: Optional[float] = Field(None, description="Current price of one token in USD.")
    value_usd: Optional[float] = Field(None, description="Total value of this token holding in USD.")
    logo_uri: Optional[str] = Field(None, description="URI for the token's logo.")

class NativeBalance(BaseModel):
    symbol: str = "SOL"
    name: str = "Solana"
    ui_amount: float = Field(..., description="SOL balance in human-readable format.")
    raw_amount: str = Field(..., description="SOL balance in lamports as a string.")
    price_usd: Optional[float] = Field(None, description="Current price of SOL in USD.")
    value_usd: Optional[float] = Field(None, description="Total value of SOL balance in USD.")

class DeFiPortfolio(BaseModel):
    wallet_address: str
    sol_balance: NativeBalance
    token_holdings: List[TokenHolding] = []
    total_spl_tokens_value_usd: Optional[float] = Field(None, description="Total value of all SPL token holdings in USD.")
    # Potential future additions:
    # total_defi_value_usd: Optional[float] = None # Including staking, lending etc.