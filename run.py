"""Launch Watchtower: starts FastAPI backend + React dev server + opens browser."""
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent
FRONTEND_DIR = ROOT / "frontend"
PORTS_FILE = ROOT / "ports.json"


def _load_ports() -> tuple[int, int]:
    """Load port config from ports.json. Creates default file if missing."""
    defaults = {"backend_port": 8080, "frontend_port": 5173}
    if not PORTS_FILE.is_file():
        PORTS_FILE.write_text(json.dumps(defaults, indent=2) + "\n")
        print(f"[watchtower] Created {PORTS_FILE} with default ports.")
    try:
        data = json.loads(PORTS_FILE.read_text())
        return int(data.get("backend_port", 8080)), int(data.get("frontend_port", 5173))
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[watchtower] Error reading {PORTS_FILE}: {e}. Using defaults.")
        return 8080, 5173


def _kill_tree(proc: subprocess.Popen) -> None:
    """Kill a process and all its children (works on Windows and Unix)."""
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass


def _preflight_local_provider() -> None:
    """If local provider is selected, ensure Ollama + model are ready before launch."""
    try:
        from backend.config import load_config
        from backend.services.intel import ensure_local_provider_ready
    except Exception as e:
        print(f"[watchtower] Local provider preflight unavailable: {e}")
        return

    try:
        cfg = load_config()
    except Exception as e:
        print(f"[watchtower] Could not load config for local provider preflight: {e}")
        return

    if cfg.llm_provider != "local":
        return

    model = cfg.llm_model or "llama3"
    print(
        f"[watchtower] Local provider selected. "
        f"Ensuring Ollama + model '{model}' are ready (auto-install if needed)..."
    )
    try:
        asyncio.run(ensure_local_provider_ready(cfg.llm_model))
        print("[watchtower] Local provider is ready.")
    except Exception as e:
        print(f"[watchtower] WARNING: Local provider setup failed: {e}")


def main():
    _preflight_local_provider()
    backend_port, frontend_port = _load_ports()
    procs: list[subprocess.Popen] = []
    kwargs = {}
    if sys.platform != "win32":
        kwargs["preexec_fn"] = os.setsid

    # Start backend
    print(f"[watchtower] Starting backend on http://localhost:{backend_port} ...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--reload", "--reload-dir", "backend", "--port", str(backend_port)],
        cwd=str(ROOT),
        **kwargs,
    )
    procs.append(backend)

    # Start frontend with custom port
    print(f"[watchtower] Starting frontend on http://localhost:{frontend_port} ...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    env = os.environ.copy()
    env["VITE_BACKEND_PORT"] = str(backend_port)
    frontend = subprocess.Popen(
        [npm_cmd, "run", "dev", "--", "--port", str(frontend_port)],
        cwd=str(FRONTEND_DIR),
        env=env,
        **kwargs,
    )
    procs.append(frontend)

    # Wait for backend to be ready
    time.sleep(3)
    if backend.poll() is not None:
        print("[watchtower] ERROR: Backend failed to start. Check the error above.")
        for p in procs:
            _kill_tree(p)
        sys.exit(1)

    print("[watchtower] Opening browser...")
    webbrowser.open(f"http://localhost:{frontend_port}")
    print("[watchtower] Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[watchtower] Shutting down...")
    finally:
        for p in procs:
            _kill_tree(p)
        print("[watchtower] Stopped.")


if __name__ == "__main__":
    main()
