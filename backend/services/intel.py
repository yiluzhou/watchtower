from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from ..models import (
    Brief,
    CountryRisk,
    DayForecast,
    LocalBrief,
    LocalCapabilitiesResponse,
    LocalGpuInfo,
    LocalModelOption,
    LocalModelRecommendations,
    LocalOllamaStatus,
    NewsItem,
    WeatherConditions,
)

PROVIDER_DEFAULTS: dict[str, dict] = {
    "groq": {
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "default_model": "llama-3.1-8b-instant",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
    },
    "openai": {
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "default_model": "gpt-4o-mini",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
    },
    "chatgpt": {
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "default_model": "gpt-4o",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
    },
    "deepseek": {
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "default_model": "deepseek-chat",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
    },
    "gemini": {
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models",
        "default_model": "gemini-1.5-flash",
        "auth_header": "X-Goog-Api-Key",
        "auth_prefix": "",
    },
    "claude": {
        "endpoint": "https://api.anthropic.com/v1/messages",
        "default_model": "claude-3-haiku-20240307",
        "auth_header": "x-api-key",
        "auth_prefix": "",
    },
    "local": {
        "endpoint": "http://localhost:11434/v1/chat/completions",
        "default_model": "llama3",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
    },
}

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_START_TIMEOUT_SEC = 20
OLLAMA_POLL_SEC = 0.5
OLLAMA_INSTALL_TIMEOUT_SEC = 20 * 60
OLLAMA_PULL_TIMEOUT_SEC = 30 * 60
OLLAMA_KEEP_ALIVE = "5m"
_OLLAMA_SETUP_LOCK = asyncio.Lock()
logger = logging.getLogger("uvicorn.error")

LOCAL_MODEL_CATALOG: list[dict] = [
    {
        "name": "qwen3.5:4b",
        "label": "Qwen 3.5 4B",
        "family": "qwen",
        "params_b": 4.0,
        "est_vram_gb": 4.0,
        "focus": "speed",
        "keywords": ["qwen", "fast", "small", "chat", "coding"],
    },
    {
        "name": "qwen3.5:9b",
        "label": "Qwen 3.5 9B",
        "family": "qwen",
        "params_b": 9.0,
        "est_vram_gb": 8.0,
        "focus": "balanced",
        "keywords": ["qwen", "balanced", "coding", "reasoning", "general"],
    },
    {
        "name": "qwen3.5:14b",
        "label": "Qwen 3.5 14B",
        "family": "qwen",
        "params_b": 14.0,
        "est_vram_gb": 12.0,
        "focus": "overall",
        "keywords": ["qwen", "reasoning", "overall", "coding", "analysis"],
    },
    {
        "name": "qwen3.5:27b",
        "label": "Qwen 3.5 27B",
        "family": "qwen",
        "params_b": 27.0,
        "est_vram_gb": 19.0,
        "focus": "reasoning",
        "keywords": ["qwen", "reasoning", "large", "deep analysis", "agent"],
    },
    {
        "name": "hf.co/Jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-GGUF:Q4_K_M",
        "label": "Jackrong Qwen 3.5 27B Opus Distilled (Q4_K_M)",
        "family": "qwen",
        "params_b": 27.0,
        "est_vram_gb": 16.5,
        "focus": "reasoning",
        "auto_pull": False,
        "install_hint": (
            "Manual import required. Download `Qwen3.5-27B.Q4_K_M.gguf` from the Hugging Face GGUF repo, "
            "then run `powershell -ExecutionPolicy Bypass -File scripts/setup_jackrong_qwen35_27b.ps1 "
            "-GgufPath /path/to/Qwen3.5-27B.Q4_K_M.gguf`."
        ),
        "keywords": [
            "qwen",
            "reasoning",
            "claude",
            "opus",
            "distilled",
            "huggingface",
            "gguf",
            "q4_k_m",
            "coding",
            "analysis",
        ],
    },
    {
        "name": "llama3.1:8b",
        "label": "Llama 3.1 8B",
        "family": "llama",
        "params_b": 8.0,
        "est_vram_gb": 7.0,
        "focus": "speed",
        "keywords": ["llama", "fast", "general", "chat"],
    },
    {
        "name": "llama3.3:70b",
        "label": "Llama 3.3 70B",
        "family": "llama",
        "params_b": 70.0,
        "est_vram_gb": 42.0,
        "focus": "reasoning",
        "keywords": ["llama", "reasoning", "very large", "multilingual"],
    },
    {
        "name": "deepseek-r1:14b",
        "label": "DeepSeek R1 14B",
        "family": "deepseek",
        "params_b": 14.0,
        "est_vram_gb": 12.0,
        "focus": "reasoning",
        "keywords": ["deepseek", "reasoning", "math", "logic", "analysis"],
    },
]


def _get_model(provider: str, model: str) -> str:
    if model:
        return model
    return PROVIDER_DEFAULTS.get(provider, {}).get("default_model", "llama3")


def _get_endpoint(provider: str, model: str) -> str:
    defaults = PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS["local"])
    endpoint = defaults["endpoint"]
    if provider == "gemini":
        m = model or defaults["default_model"]
        return f"{endpoint}/{m}:generateContent"
    return endpoint


def _get_auth_header(provider: str) -> str:
    return PROVIDER_DEFAULTS.get(provider, {}).get("auth_header", "Authorization")


def _get_auth_value(provider: str, api_key: str) -> str:
    prefix = PROVIDER_DEFAULTS.get(provider, {}).get("auth_prefix", "Bearer ")
    return prefix + api_key


async def _fetch_ollama_tags() -> dict:
    async with httpx.AsyncClient(timeout=3) as client:
        resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
        resp.raise_for_status()
        return resp.json()


def _extract_ollama_models(tags_payload: dict) -> set[str]:
    models = tags_payload.get("models", []) or []
    names: set[str] = set()
    for model in models:
        if not isinstance(model, dict):
            continue
        name = str(model.get("name", "")).strip()
        alias = str(model.get("model", "")).strip()
        if name:
            names.add(name)
        if alias:
            names.add(alias)
    return names


def _detect_gpu_info() -> LocalGpuInfo:
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            proc = subprocess.run(
                [
                    nvidia_smi,
                    "--query-gpu=name,memory.total,memory.free,driver_version",
                    "--format=csv,noheader,nounits",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                first = proc.stdout.strip().splitlines()[0]
                parts = [p.strip() for p in first.split(",")]
                if len(parts) >= 4:
                    total_mb = float(parts[1])
                    free_mb = float(parts[2])
                    return LocalGpuInfo(
                        name=parts[0],
                        driver_version=parts[3],
                        total_vram_gb=round(total_mb / 1024, 1),
                        free_vram_gb=round(free_mb / 1024, 1),
                        detection="nvidia-smi",
                    )
        except Exception:
            pass

    return LocalGpuInfo()


async def _get_ollama_status() -> LocalOllamaStatus:
    binary = _resolve_ollama_binary() or ""
    status = LocalOllamaStatus(
        installed=bool(binary),
        running=False,
        binary_path=binary,
        installed_models=[],
    )
    try:
        tags = await _fetch_ollama_tags()
        status.running = True
        status.installed_models = sorted(_extract_ollama_models(tags))
    except Exception:
        pass
    return status


def _normalize_model_name(name: str) -> str:
    n = (name or "").strip()
    if not n:
        return "llama3"
    return n


def resolve_local_model_name(model: str) -> str:
    return _get_model("local", model)


def _resolve_ollama_binary() -> str | None:
    path = shutil.which("ollama")
    if path:
        return path

    candidates: list[Path] = []
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            candidates.append(Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe")
    else:
        candidates.extend(
            [
                Path("/usr/local/bin/ollama"),
                Path("/opt/homebrew/bin/ollama"),
                Path("/usr/bin/ollama"),
            ]
        )

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def _auto_install_ollama() -> str:
    logger.info("Local provider: Ollama not found. Attempting automatic installation.")

    commands: list[list[str]] = []
    if sys.platform == "win32":
        winget = shutil.which("winget")
        if winget:
            commands.append(
                [
                    winget,
                    "install",
                    "-e",
                    "--id",
                    "Ollama.Ollama",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                    "--disable-interactivity",
                    "--scope",
                    "user",
                    "--silent",
                ]
            )
    elif sys.platform == "darwin":
        brew = shutil.which("brew")
        if brew:
            commands.append([brew, "install", "ollama"])
    else:
        if shutil.which("sh") and shutil.which("curl"):
            commands.append(["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"])

    if not commands:
        raise RuntimeError(
            "Ollama is not installed and automatic installation is unavailable "
            "on this system (no supported installer found)."
        )

    last_error = "installer did not run"
    for cmd in commands:
        logger.info("Local provider: running installer command: %s", " ".join(cmd))
        try:
            proc = subprocess.run(
                cmd,
                check=False,
                stdout=None,
                stderr=None,
                timeout=OLLAMA_INSTALL_TIMEOUT_SEC,
            )
            if proc.returncode != 0:
                last_error = f"installer exited with code {proc.returncode}"
            path = _resolve_ollama_binary()
            if path:
                logger.info("Local provider: Ollama installation succeeded (%s).", path)
                return path
        except subprocess.TimeoutExpired:
            last_error = f"installer timed out after {OLLAMA_INSTALL_TIMEOUT_SEC} seconds"

    path = _resolve_ollama_binary()
    if path:
        logger.info("Local provider: Ollama installation succeeded (%s).", path)
        return path

    raise RuntimeError(
        f"Ollama is not installed and automatic installation failed ({last_error})."
    )


def _require_ollama_binary() -> str:
    path = _resolve_ollama_binary()
    if path:
        return path
    return _auto_install_ollama()


def _model_available(requested: str, available: set[str]) -> bool:
    normalized_requested = requested.strip().lower()
    normalized_available = {a.strip().lower() for a in available if a}

    if normalized_requested in normalized_available:
        return True

    if ":" not in normalized_requested and f"{normalized_requested}:latest" in normalized_available:
        return True

    # Only treat tag variants as interchangeable when the request omitted a tag.
    if ":" not in normalized_requested:
        req_base = normalized_requested.split(":", 1)[0]
        return any(a.split(":", 1)[0] == req_base for a in normalized_available)

    return False


def _start_ollama_serve() -> None:
    ollama_bin = _require_ollama_binary()

    logger.info("Local provider: starting Ollama server (`ollama serve`).")

    kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        creation_flags = 0
        creation_flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        creation_flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        if creation_flags:
            kwargs["creationflags"] = creation_flags
    else:
        kwargs["start_new_session"] = True

    subprocess.Popen([ollama_bin, "serve"], **kwargs)


async def _wait_for_ollama(timeout_sec: float) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            await _fetch_ollama_tags()
            return True
        except Exception:
            await asyncio.sleep(OLLAMA_POLL_SEC)
    return False


def _pull_ollama_model(model_name: str) -> None:
    ollama_bin = _require_ollama_binary()
    cmd = [ollama_bin, "pull", model_name]
    logger.info(
        "Local provider: model '%s' not found. Pulling now (this can take several minutes)...",
        model_name,
    )
    try:
        proc = subprocess.run(
            cmd,
            stdout=None,
            stderr=None,
            check=False,
            timeout=OLLAMA_PULL_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Timed out pulling Ollama model '{model_name}'. "
            f"Run `ollama pull {model_name}` manually."
        ) from exc
    if proc.returncode != 0:
        raise RuntimeError(
            f"Failed to pull Ollama model '{model_name}'. "
            f"Run `ollama pull {model_name}` manually."
        )
    logger.info("Local provider: model '%s' pulled successfully.", model_name)


def _stop_ollama_model(model_name: str) -> bool:
    normalized = _normalize_model_name(model_name)
    ollama_bin = _resolve_ollama_binary()
    if not ollama_bin:
        logger.info(
            "Local provider: skip stopping model '%s' because Ollama is not installed.",
            normalized,
        )
        return False

    cmd = [ollama_bin, "stop", normalized]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        logger.warning("Local provider: timed out stopping model '%s'.", normalized)
        return False

    if proc.returncode == 0:
        logger.info("Local provider: model '%s' stopped.", normalized)
        return True

    detail = "\n".join(part.strip() for part in (proc.stdout, proc.stderr) if part and part.strip())
    detail_l = detail.lower()
    if "not found" in detail_l or "not running" in detail_l:
        logger.info("Local provider: model '%s' was not running.", normalized)
        return False

    logger.warning(
        "Local provider: failed to stop model '%s' (exit %s): %s",
        normalized,
        proc.returncode,
        detail or "unknown error",
    )
    return False


async def _ensure_local_ollama_ready(model_name: str) -> None:
    normalized = _normalize_model_name(model_name)
    async with _OLLAMA_SETUP_LOCK:
        logger.info("Local provider: validating Ollama for model '%s'.", normalized)
        try:
            tags = await _fetch_ollama_tags()
        except Exception:
            logger.info(
                "Local provider: Ollama is not reachable at %s, attempting auto-start.",
                OLLAMA_BASE_URL,
            )
            _start_ollama_serve()
            if not await _wait_for_ollama(OLLAMA_START_TIMEOUT_SEC):
                raise RuntimeError(
                    "Could not start Ollama automatically. "
                    "Run `ollama serve` and try again."
                )
            logger.info("Local provider: Ollama server is reachable.")
            tags = await _fetch_ollama_tags()

        available = _extract_ollama_models(tags)
        if _model_available(normalized, available):
            logger.info("Local provider: model '%s' is ready.", normalized)
            return

        catalog_item = _get_catalog_model(normalized)
        if catalog_item and not catalog_item.get("auto_pull", True):
            raise RuntimeError(str(catalog_item.get("install_hint") or "Manual import required for this model."))

        await asyncio.to_thread(_pull_ollama_model, normalized)

        refreshed = await _fetch_ollama_tags()
        refreshed_models = _extract_ollama_models(refreshed)
        if not _model_available(normalized, refreshed_models):
            raise RuntimeError(
                f"Model '{normalized}' is still unavailable in Ollama after setup."
            )


async def ensure_local_provider_ready(model: str) -> None:
    await _ensure_local_ollama_ready(_get_model("local", model))


async def stop_local_provider_model(model: str) -> bool:
    return await asyncio.to_thread(_stop_ollama_model, resolve_local_model_name(model))


def schedule_local_provider_warmup(model: str) -> None:
    async def _runner() -> None:
        try:
            await ensure_local_provider_ready(model)
        except Exception as exc:
            # Suppress task crash, but keep the reason visible in server logs.
            logger.warning("Local provider warmup failed: %s", exc)
            return

    asyncio.create_task(_runner())


def _fit_for_vram(free_vram_gb: float, est_vram_gb: float) -> str:
    if free_vram_gb <= 0:
        return "unknown"
    if free_vram_gb >= est_vram_gb*1.25:
        return "great"
    if free_vram_gb >= est_vram_gb*1.05:
        return "ok"
    if free_vram_gb >= est_vram_gb*0.90:
        return "tight"
    return "too_big"


def _get_catalog_model(model_name: str) -> dict | None:
    normalized = _normalize_model_name(model_name).lower()
    return next(
        (item for item in LOCAL_MODEL_CATALOG if str(item.get("name", "")).strip().lower() == normalized),
        None,
    )


def _pick_recommendations(models: list[LocalModelOption]) -> LocalModelRecommendations:
    feasible = [m for m in models if m.fit in ("great", "ok", "tight")]
    if not feasible:
        return LocalModelRecommendations(
            qwen35_27b_can_run=False,
            qwen35_27b_note="No catalog model appears feasible with current free VRAM.",
        )

    def reasoning_score(m: LocalModelOption) -> float:
        return m.params_b + (3 if m.focus in ("reasoning", "overall") else 0)

    def speed_score(m: LocalModelOption) -> float:
        return -m.est_vram_gb + (2 if m.focus == "speed" else 0)

    def overall_score(m: LocalModelOption) -> float:
        return m.params_b*0.6 - m.est_vram_gb*0.2 + (2 if m.focus in ("overall", "balanced") else 0)

    best_reasoning = max(feasible, key=reasoning_score).name
    best_speed = max(feasible, key=speed_score).name
    best_overall = max(feasible, key=overall_score).name

    qwen27 = next((m for m in models if m.name == "qwen3.5:27b"), None)
    if qwen27 and qwen27.fit in ("great", "ok", "tight"):
        qwen_note = (
            "Likely runnable on GPU with quantized weights. "
            "Use a moderate context window for best stability."
        )
        can_run_qwen = True
    elif qwen27:
        qwen_note = (
            "Unlikely to fit comfortably in current free VRAM. "
            "Use a smaller model or reduce memory pressure."
        )
        can_run_qwen = False
    else:
        qwen_note = "Qwen 3.5 27B not present in catalog."
        can_run_qwen = False

    return LocalModelRecommendations(
        best_reasoning=best_reasoning,
        best_speed=best_speed,
        best_overall=best_overall,
        qwen35_27b_can_run=can_run_qwen,
        qwen35_27b_note=qwen_note,
    )


async def get_local_capabilities() -> LocalCapabilitiesResponse:
    gpu = _detect_gpu_info()
    ollama = await _get_ollama_status()
    installed = {m.lower() for m in ollama.installed_models}

    options: list[LocalModelOption] = []
    for item in LOCAL_MODEL_CATALOG:
        name = item["name"]
        fit = _fit_for_vram(gpu.free_vram_gb, float(item["est_vram_gb"]))
        options.append(
            LocalModelOption(
                name=name,
                label=item["label"],
                family=item["family"],
                params_b=float(item["params_b"]),
                est_vram_gb=float(item["est_vram_gb"]),
                focus=item["focus"],
                keywords=item["keywords"],
                installed=name.lower() in installed,
                fit=fit,
                auto_pull=bool(item.get("auto_pull", True)),
                install_hint=str(item.get("install_hint", "")),
            )
        )

    recs = _pick_recommendations(options)

    return LocalCapabilitiesResponse(
        gpu=gpu,
        ollama=ollama,
        recommendations=recs,
        models=options,
        generated_at=datetime.now(timezone.utc),
    )


def _build_global_prompt(items: list[NewsItem]) -> str:
    limit = min(40, len(items))
    headlines = "\n".join(
        f"{i+1}. [{item.threat_level.name}] {item.title} ({item.source})"
        for i, item in enumerate(items[:limit])
    )
    return f"""You are a geopolitical intelligence analyst. Analyze these recent headlines and respond in EXACTLY this format with no extra text:

SUMMARY:
<3-4 sentences covering the most critical global developments right now>

THREATS:
\u2022 <threat 1, one line>
\u2022 <threat 2, one line>
\u2022 <threat 3, one line>
\u2022 <threat 4, one line>
\u2022 <threat 5, one line>

COUNTRY_RISKS:
<CountryName>|<score 0-100>|<one short reason phrase>
<CountryName>|<score 0-100>|<one short reason phrase>
<CountryName>|<score 0-100>|<one short reason phrase>
<CountryName>|<score 0-100>|<one short reason phrase>
<CountryName>|<score 0-100>|<one short reason phrase>
<CountryName>|<score 0-100>|<one short reason phrase>
<CountryName>|<score 0-100>|<one short reason phrase>
<CountryName>|<score 0-100>|<one short reason phrase>

Rules:
- SUMMARY: factual, analyst-toned, no fluff, max 3 sentences
- THREATS: exactly 5 bullets, one line each, most severe first
- COUNTRY_RISKS: exactly 8 countries most prominent in the news, score reflects current instability/risk (100=active war, 0=stable), pipe-separated, short reason (3-5 words max)
- No markdown, no extra formatting, no preamble

HEADLINES:
{headlines}"""


def _build_local_prompt(
    city: str,
    items: list[NewsItem],
    cond: WeatherConditions | None,
    forecast: list[DayForecast],
) -> str:
    parts: list[str] = []

    parts.append("LOCAL NEWS HEADLINES:")
    for i, item in enumerate(items[:20]):
        parts.append(f"{i+1}. {item.title} ({item.source})")

    if cond:
        parts.append("\nCURRENT WEATHER:")
        parts.append(f"Location: {cond.city}")
        parts.append(f"Temperature: {cond.temp_c:.1f}\u00b0C (feels like {cond.feels_like_c:.1f}\u00b0C)")
        parts.append(f"Conditions: {cond.icon} {cond.description}")
        parts.append(f"Humidity: {cond.humidity}%, Wind: {cond.wind_speed_kmh:.0f} km/h, UV: {cond.uv_index:.0f}")

    parts.append("\nFORECAST (next 5 days):")
    for f in forecast[:5]:
        parts.append(f"- {f.date}: {f.icon} {f.desc}, High: {f.max_temp_c:.0f}\u00b0C, Low: {f.min_temp_c:.0f}\u00b0C, Rain: {f.rain_mm:.1f}mm")

    data_str = "\n".join(parts)
    return f"""You are a local news and weather analyst. Summarize this information for {city} in 2-3 sentences.
Focus on:
1. Any notable local news stories
2. Current weather conditions and any weather concerns for the coming days
3. Short summary of the news stories

Respond in this exact format with no extra text:

SUMMARY:
<2-3 sentence summary>

Rules:
- Keep it concise and practical
- No markdown formatting
- Lead with the most important information
- Never send back the 'DATA' as is, always explain

DATA:
{data_str}"""


def _strip_ollama_chat_artifacts(content: str) -> str:
    cleaned = (content or "").strip()
    for marker in ("<|endoftext|>", "<|im_start|>", "<|im_end|>"):
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[0].strip()
    return cleaned


def _looks_like_placeholder(text: str) -> bool:
    stripped = text.strip().lower()
    return stripped.startswith("<") and stripped.endswith(">")


def _parse_brief_response(content: str) -> tuple[str, list[str], list[CountryRisk]]:
    content = _strip_ollama_chat_artifacts(content)
    sections: dict[str, str] = {}
    current = ""
    buf: list[str] = []

    for line in content.split("\n"):
        trimmed = line.strip()
        normalized = trimmed.strip("*").strip()
        if normalized in ("SUMMARY:", "THREATS:", "COUNTRY_RISKS:"):
            if current:
                section_text = "\n".join(buf).strip()
                if section_text and current not in sections:
                    sections[current] = section_text
            current = normalized.rstrip(":")
            buf = []
        elif current:
            buf.append(line)
    if current:
        section_text = "\n".join(buf).strip()
        if section_text and current not in sections:
            sections[current] = section_text

    summary = sections.get("SUMMARY", "")
    if _looks_like_placeholder(summary):
        summary = ""

    threats: list[str] = []
    for line in sections.get("THREATS", "").split("\n"):
        line = line.strip().lstrip("\u2022-*").strip()
        if line and not _looks_like_placeholder(line):
            threats.append(line)

    risks: list[CountryRisk] = []
    for line in sections.get("COUNTRY_RISKS", "").split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split("|", 2)
        if len(parts) < 2:
            continue
        country = parts[0].strip()
        try:
            score = int(parts[1].strip())
        except ValueError:
            continue
        if not country:
            continue
        reason = parts[2].strip() if len(parts) == 3 else ""
        risks.append(CountryRisk(country=country, score=max(0, min(100, score)), reason=reason))

    if not summary:
        summary_lines: list[str] = []
        for line in content.split("\n"):
            stripped = line.strip()
            normalized = stripped.strip("*").strip()
            if not stripped:
                if summary_lines:
                    break
                continue
            if normalized in ("SUMMARY:", "THREATS:", "COUNTRY_RISKS:"):
                continue
            if "|" in stripped and len(stripped.split("|", 2)) >= 2:
                continue
            if stripped.lstrip("\u2022-*").strip() != stripped:
                continue
            if _looks_like_placeholder(stripped):
                continue
            summary_lines.append(stripped)
        summary = " ".join(summary_lines).strip() or content.strip()

    return summary, threats, risks


def _parse_local_brief_response(content: str) -> str:
    content = _strip_ollama_chat_artifacts(content)
    in_summary = False
    lines: list[str] = []
    for line in content.split("\n"):
        trimmed = line.strip()
        if trimmed.startswith("SUMMARY:"):
            in_summary = True
            continue
        if in_summary and trimmed and not _looks_like_placeholder(trimmed):
            lines.append(trimmed)
    return " ".join(lines) if lines else content.strip()


async def _call_openai_compatible(
    provider: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
) -> tuple[str, str]:
    model_name = _get_model(provider, model)
    if provider == "local":
        await _ensure_local_ollama_ready(model_name)

    body = {
        "model": model_name,
        "temperature": 0,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers: dict[str, str] = {"Content-Type": "application/json"}
    # Local/Ollama doesn't need auth, but include it if provided
    if api_key or provider != "local":
        headers[_get_auth_header(provider)] = _get_auth_value(provider, api_key)

    endpoint = _get_endpoint(provider, model)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(endpoint, json=body, headers=headers)
            resp.raise_for_status()
            result = resp.json()
    except httpx.ConnectError:
        if provider == "local":
            # One more setup/retry pass in case Ollama was slow to come up.
            await _ensure_local_ollama_ready(model_name)
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(endpoint, json=body, headers=headers)
                resp.raise_for_status()
                result = resp.json()
        else:
            raise RuntimeError(f"Cannot connect to {provider} API")
    except httpx.HTTPStatusError as exc:
        if provider == "local":
            detail = exc.response.text.strip() or f"HTTP {exc.response.status_code}"
            raise RuntimeError(f"Ollama request failed: {detail}") from exc
        raise RuntimeError(f"{provider} HTTP {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        if provider == "local":
            raise RuntimeError(f"Ollama request failed: {exc}") from exc
        raise RuntimeError(f"Cannot connect to {provider} API")

    choices = result.get("choices", [])
    if not choices:
        raise RuntimeError(f"No response from {provider}")
    return choices[0]["message"]["content"], result.get("model", _get_model(provider, model))


async def _call_ollama_native(
    model: str,
    prompt: str,
    system: str,
    max_tokens: int,
) -> tuple[str, str]:
    model_name = _get_model("local", model)
    await _ensure_local_ollama_ready(model_name)

    body = {
        "model": model_name,
        "stream": False,
        "think": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "options": {
            "temperature": 0,
            "num_predict": max_tokens,
            "stop": ["<|endoftext|>", "<|im_start|>", "<|im_end|>"],
        },
    }
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=body)
            resp.raise_for_status()
            result = resp.json()
    except httpx.ConnectError as exc:
        await _ensure_local_ollama_ready(model_name)
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=body)
                resp.raise_for_status()
                result = resp.json()
        except httpx.HTTPError as retry_exc:
            raise RuntimeError(f"Ollama request failed: {retry_exc}") from retry_exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip() or f"HTTP {exc.response.status_code}"
        raise RuntimeError(f"Ollama request failed: {detail}") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc

    message = result.get("message") or {}
    content = (message.get("content") or "").strip()
    if not content:
        reasoning = (message.get("thinking") or message.get("reasoning") or "").strip()
        if reasoning:
            content = reasoning
    content = _strip_ollama_chat_artifacts(content)
    if not content:
        raise RuntimeError("Ollama returned an empty response")
    return content, result.get("model", model_name)


async def _call_claude(
    api_key: str,
    model: str,
    prompt: str,
    system: str,
    max_tokens: int,
) -> tuple[str, str]:
    model_name = _get_model("claude", model)
    body = {
        "model": model_name,
        "max_tokens": max_tokens,
        "temperature": 0,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(PROVIDER_DEFAULTS["claude"]["endpoint"], json=body, headers=headers)
        resp.raise_for_status()
        result = resp.json()

    content_blocks = result.get("content", [])
    if not content_blocks:
        raise RuntimeError("No response from Claude")
    return content_blocks[0]["text"], model_name


async def _call_gemini(
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
) -> tuple[str, str]:
    model_name = _get_model("gemini", model)
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": max_tokens},
    }
    endpoint = _get_endpoint("gemini", model)
    headers = {
        "X-Goog-Api-Key": api_key,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(endpoint, json=body, headers=headers)
        resp.raise_for_status()
        result = resp.json()

    candidates = result.get("candidates", [])
    if not candidates or not candidates[0].get("content", {}).get("parts"):
        raise RuntimeError("No response from Gemini")
    return candidates[0]["content"]["parts"][0]["text"], model_name


async def _call_llm(
    provider: str,
    api_key: str,
    model: str,
    prompt: str,
    system: str,
    max_tokens: int,
) -> tuple[str, str]:
    if provider == "local":
        return await _call_ollama_native(model, prompt, system, max_tokens)
    if provider == "claude":
        return await _call_claude(api_key, model, prompt, system, max_tokens)
    if provider == "gemini":
        return await _call_gemini(api_key, model, prompt, max_tokens)
    # OpenAI-compatible: openai, chatgpt, groq, deepseek
    return await _call_openai_compatible(provider, api_key, model, prompt, max_tokens)


async def generate_brief(
    provider: str,
    api_key: str,
    model: str,
    items: list[NewsItem],
) -> Brief:
    if not api_key and provider not in ("local", "chatgpt"):
        return Brief(
            summary="No API key configured. Add one in Settings to enable AI briefings.",
            generated_at=datetime.now(timezone.utc),
            model="none",
        )

    if not items:
        return Brief(
            summary="No news items available to summarize.",
            generated_at=datetime.now(timezone.utc),
            model="none",
        )

    prompt = _build_global_prompt(items)
    content, model_used = await _call_llm(
        provider, api_key, model, prompt,
        "You are a geopolitical intelligence analyst.",
        700,
    )
    summary, threats, risks = _parse_brief_response(content)
    if not summary:
        summary = content.strip()

    return Brief(
        summary=summary,
        key_threats=threats,
        country_risks=risks,
        generated_at=datetime.now(timezone.utc),
        model=model_used,
    )


async def generate_local_brief(
    provider: str,
    api_key: str,
    model: str,
    city: str,
    items: list[NewsItem],
    conditions: WeatherConditions | None,
    forecast: list[DayForecast],
) -> LocalBrief:
    if not api_key and provider not in ("local", "chatgpt"):
        return LocalBrief(
            summary="No API key configured. Add one in Settings to enable AI briefings.",
            generated_at=datetime.now(timezone.utc),
            model="none",
        )

    prompt = _build_local_prompt(city, items, conditions, forecast)
    content, model_used = await _call_llm(
        provider, api_key, model, prompt,
        "You are a local news and weather analyst.",
        300,
    )
    summary = _parse_local_brief_response(content)

    return LocalBrief(
        summary=summary,
        generated_at=datetime.now(timezone.utc),
        model=model_used,
    )
