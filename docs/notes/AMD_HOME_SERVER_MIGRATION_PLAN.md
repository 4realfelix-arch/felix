# AMD Home Server Migration Plan (from NVIDIA fork)

This repo started as a fork of an NVIDIA-oriented server and is being adapted to run on an AMD home server (ROCm/HIP).

## Goal

- Run Felix locally on the AMD machine with predictable, repeatable setup.
- Remove “CUDA/NVIDIA default” assumptions from docs/scripts.
- Make GPU usage **configurable** (CPU fallback always works).
- Keep optional integrations (OpenMemory, MPD, ComfyUI) truly optional.

## Current Reality (as of Dec 16, 2025)

- Flyouts already exist as a stable UI surface (`browser`/`code`/`terminal`) and tools can trigger them by returning `{ "flyout": {"type": ..., "content": ...} }`.
- STT currently uses `server/stt/whisper.py` (faster-whisper) and defaults to `WHISPER_DEVICE=auto` in `server/config.py` (cross-vendor default).
- There is also a ROCm-oriented `server/stt/whisper_cpp.py` (whisper.cpp HIP path) still present.
- Startup script `run.sh` contains hard-coded paths for OpenMemory (`/home/stacy/openmemory`) and tries to auto-start MPD/OpenMemory.

## Migration Strategy

### 1) Make the machine “GPU-ready” (ROCm)

- Install ROCm matching the GPU generation and OS.
- Confirm ROCm sees the GPUs:

```bash
rocm-smi
/opt/rocm/bin/rocminfo | head
```

If ROCm is not stable, the system must still run on CPU (STT CPU + LLM CPU).

### 2) Pick the STT backend for AMD

You have two viable paths (select with `STT_BACKEND`):

**A) Whisper.cpp + HIP (recommended for MI50/ROCm if you already have it working):**
- Use `server/stt/whisper_cpp.py` and compile whisper.cpp with HIP support.
- Pros: AMD-native path.
- Cons: extra build step and model format management.

Setup guide: `docs/notes/WHISPER_CPP_HIP_SETUP.md`.

**B) faster-whisper (CPU fallback; GPU depends on platform support):**
- Keep `server/stt/whisper.py`.
- Pros: simplest Python integration.
- Cons: “GPU” acceleration is not guaranteed on ROCm; treat it as CPU-first unless verified.

**Plan:** introduce an explicit setting like `STT_BACKEND=faster-whisper|whisper-cpp` and route `get_stt()` accordingly (so switching is just config).

### 3) LLM backend on AMD

- If you rely on Ollama, confirm you can run Ollama on this machine (ROCm build or CPU).
- If not, use an OpenAI-compatible backend (LM Studio, etc.) via the existing `llm_backend` settings.

### 4) TTS on AMD

- Piper is CPU-based here; keep it as the default.
- If Piper voice install breaks on the AMD box, use the existing `docs/notes/TTS_FIX_NEEDED.md` procedure.

### 5) ComfyUI (optional)

- Treat ComfyUI as a separate optional service.
- Only enable image tools if ComfyUI starts cleanly.

## Repo Changes to Make (the “missing plan” tasks)

### A) Remove CUDA/NVIDIA defaults

- Change defaults from `cuda` → `auto` where possible:
  - `WHISPER_DEVICE=auto`
  - VAD device selection should not assume CUDA.
- Avoid logging that claims “CUDA GPU” when running on AMD.

### B) Make `run.sh` machine-agnostic

- Remove hard-coded `/home/stacy/openmemory` and make OpenMemory optional without path assumptions.
- Prefer:
  - `OPENMEMORY_DIR` env var if present
  - otherwise “don’t auto-start” (just warn)

### C) Add explicit backend toggles

- Add `STT_BACKEND` and (if needed) `TTS_ENGINE` selection.
- Keep CPU fallback behavior for everything.

### D) Add an AMD-specific quickstart snippet

- Document the minimal env settings for AMD:

```env
WHISPER_DEVICE=auto
WHISPER_COMPUTE_TYPE=float16
LLM_BACKEND=ollama
# Optional:
DISABLED_TOOL_MODULES=music_tools,memory_tools
ENABLED_TOOL_PACKS=flyouts_demo
```

## Validation Checklist (run on the AMD server)

```bash
python3 scripts/test_imports.py
pytest -q tests
./run.sh
```

Then in the UI:
- Trigger a flyout tool: ask for `demo_flyout_card` (when enabled).
- Confirm VAD → STT → LLM → TTS loop works end-to-end.

## Rollback Strategy

- Always keep a CPU-only configuration that works:
  - `WHISPER_DEVICE=cpu`
  - Use LLM backend that works on CPU
  - Keep ComfyUI disabled

That way GPU/ROCm issues don’t block development.
