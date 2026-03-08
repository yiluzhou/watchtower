# Watchtower

Watchtower is a global intelligence dashboard for fast situational awareness: world news, local news, weather, markets, and an AI-generated intel brief in one place.

The original project started as a Go terminal app. This repo now includes a rewritten Python web stack as the primary experience: FastAPI on the backend, React + Vite on the frontend. The legacy Go TUI is still included and remains runnable.

## What Changed

- Rewritten around a Python web app for a browser-based dashboard.
- Added local LLM support through Ollama.
- Kept the original Go TUI in the repo as a legacy interface.

## Current App Modes

### Web UI (primary)

- Backend: FastAPI + uvicorn
- Frontend: React 19 + Vite + TypeScript
- Launch command: `python run.py`

Tabs in the web app:

- Overview
- Global News
- Local
- Settings

### Go TUI (legacy)

- Bubble Tea + Lip Gloss
- Launch command: `go run .`

## Features

- AI intel brief with global summary, key threats, and country risk scoring
- Global and local RSS news feeds with keyword-based threat classification
- Current weather plus forecast
- Crypto, indices, commodities, and Polymarket tracking
- Provider switching across hosted APIs and local Ollama models
- Disk-backed caching for generated briefs

## Quick Start

### 1. Backend dependencies

Python 3.14+ is recommended.

```bash
pip install -r backend/requirements.txt
```

### 2. Frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 3. Run the web app

```bash
python run.py
```

Default ports are stored in `ports.json`:

- backend: `8080`
- frontend: `5173`

## Local LLM Support

Watchtower supports a local provider through Ollama. Select `Local (Ollama)` in Settings, then choose a model.

Currently available local model options:

- `qwen3.5:4b`
- `qwen3.5:9b`
- `qwen3.5:14b`
- `qwen3.5:27b`
- `hf.co/Jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-GGUF:Q4_K_M`
- `llama3.1:8b`
- `llama3.3:70b`
- `deepseek-r1:14b`

Notes:

- Standard Ollama models can be pulled automatically when selected.
- The Jackrong GGUF model is supported, but requires manual import into Ollama first.
- Watchtower now stops the previous Ollama model when switching models and releases the local model on app shutdown.

### Jackrong GGUF setup

This model is available in the UI, but it is not auto-pulled. Import it into Ollama manually.

1. Download `Qwen3.5-27B.Q4_K_M.gguf`
2. Save it somewhere local, for example `E:\Models\Qwen3.5-27B.Q4_K_M.gguf`
3. Run:

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts\setup_jackrong_qwen35_27b.ps1 -GgufPath E:\Models\Qwen3.5-27B.Q4_K_M.gguf
```

4. Verify:

```powershell
ollama list
```

## Supported AI Providers

- Groq
- OpenAI
- ChatGPT subscription
- Anthropic Claude
- DeepSeek
- Google Gemini
- Local (Ollama)

## Run Individual Pieces

### Backend only

```bash
uvicorn backend.main:app --reload --port 8080
```

### Frontend only

```bash
cd frontend
npm run dev
```

### Legacy Go TUI

```bash
go run .
```

## Project Structure

### Web app

- `backend/main.py`: FastAPI app and router registration
- `backend/routers/`: API routes
- `backend/services/`: feeds, markets, weather, and LLM integrations
- `backend/models.py`: shared backend models
- `frontend/src/components/`: dashboard tabs and panels
- `frontend/src/hooks/useApi.ts`: frontend API hooks
- `run.py`: launches backend + frontend together

### Legacy Go app

- `main.go`: TUI entry point
- `ui/`: Bubble Tea interface
- `feeds/`, `markets/`, `weather/`, `intel/`: data services

## Configuration

Runtime files:

- config: `~/.config/watchtower/config.yaml`
- brief cache: `~/.cache/watchtower/brief.json`
- local brief cache: `~/.cache/watchtower/local_brief.json`

Environment override:

- `LLM_API_KEY`

## Data Sources

- RSS feeds
- Open-Meteo
- CoinGecko
- Yahoo Finance
- Polymarket
- LLM provider APIs

## Legacy Installer

`install.sh` is for the original release-oriented Go CLI/TUI workflow. It is not the main installation path for the current Python web app.

## License

MIT
