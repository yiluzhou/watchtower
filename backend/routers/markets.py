from fastapi import APIRouter

from ..config import load_config
from ..models import MarketsResponse
from ..services.markets import fetch_all_markets

router = APIRouter(prefix="/api/markets", tags=["markets"])


@router.get("", response_model=MarketsResponse)
async def get_markets():
    cfg = load_config()
    data = await fetch_all_markets(cfg.crypto_pairs)
    return MarketsResponse(**data)
