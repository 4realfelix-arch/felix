#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+##############################################
# Felix Voice Agent

Fully local, real-time voice assistant with barge-in (interrupt) support.

## Quick start

```bash
./run.sh
```

- Open `http://localhost:8000` (use `localhost`, not an IP, for mic permissions).
- Config: copy `.env.example` → `.env` (loaded by `server/config.py`).

## Architecture (big picture)

- Frontend (PWA, no build step): `frontend/static/app.module.js`
- Backend entrypoint: `server/main.py` (`/ws` WebSocket, `/health`, `/api/models`, `/api/voices`)
- Session state machine: `server/session.py` (`IDLE → LISTENING → PROCESSING → SPEAKING → INTERRUPTED`)
- Pipeline: VAD (`server/audio/vad.py`) → STT (`server/stt/whisper.py`, faster-whisper) → LLM (`server/llm/ollama.py`) → TTS (`server/tts/piper_tts.py`)
- Tools: `server/tools/registry.py` + imports in `server/tools/builtin/__init__.py`
- Optional images: ComfyUI service (`server/comfy_service.py`) + tools (`server/tools/builtin/image_tools.py`)

## Layout

- `docs/`: canonical docs (`docs/DEVELOPMENT.md`, `docs/ARCHITECTURE.md`, `docs/API.md`)
- `scripts/`: dev utilities (see `scripts/README.md`)
- `review/`: moved backups/reports/media (see `review/README.md`)

## Tests

```bash
python scripts/test_imports.py
pytest -q
```
