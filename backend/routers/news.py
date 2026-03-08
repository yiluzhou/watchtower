from fastapi import APIRouter

from ..config import load_config
from ..services.feeds import fetch_global_news, fetch_local_news
from ..models import NewsItem

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/global", response_model=list[NewsItem])
async def get_global_news():
    return await fetch_global_news()


@router.get("/local", response_model=list[NewsItem])
async def get_local_news():
    cfg = load_config()
    return await fetch_local_news(cfg.location.city, cfg.location.country)
