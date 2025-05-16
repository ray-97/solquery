from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class NFTHolding(BaseModel):
    mint_address: str = Field(..., alias="id", description="The mint address (ID) of the NFT.")
    name: Optional[str] = Field("Unknown NFT Name", description="Name of the NFT (might be fetched from json_uri).")
    image_uri: Optional[str] = Field(None, description="Primary image URI for the NFT.")
    cdn_image_uri: Optional[str] = Field(None, description="CDN cached image URI, if available.")
    json_uri: Optional[str] = Field(None, description="URI to the off-chain JSON metadata.")
    collection_mint_id: Optional[str] = Field(None, description="Mint address of the collection this NFT belongs to.")
    collection_name: Optional[str] = Field("Unknown Collection", description="Name of the collection.")
    floor_price_usd: Optional[float] = Field(None, description="Estimated floor price of the NFT's collection in USD (if available).")

class NFTPortfolio(BaseModel):
    wallet_address: str
    nft_holdings: List[NFTHolding] = []
    total_nfts_count: int = 0
    # estimated_total_floor_value_usd: Optional[float] = None