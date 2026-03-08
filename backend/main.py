from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import load_config
from .routers import news, markets, weather, intel, config_router
from .services.intel import schedule_local_provider_warmup, stop_local_provider_model

app = FastAPI(title="Watchtower API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(news.router)
app.include_router(markets.router)
app.include_router(weather.router)
app.include_router(intel.router)
app.include_router(config_router.router)


@app.on_event("startup")
async def startup_warmup():
    cfg = load_config()
    if cfg.llm_provider == "local":
        # Warm up local provider in background so first brief request doesn't fail.
        schedule_local_provider_warmup(cfg.llm_model)


@app.on_event("shutdown")
async def shutdown_release_local_model():
    cfg = load_config()
    if cfg.llm_provider == "local":
        await stop_local_provider_model(cfg.llm_model)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
