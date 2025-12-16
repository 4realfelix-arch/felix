# 2025-12-17 — NVIDIA machine note

Context: We’ll be back on the NVIDIA/work machine tomorrow. We’re treating this project as two “teams”:
- Work/NVIDIA machine (fast iteration, CUDA-capable)
- Home/AMD machine (ROCm/HIP + CPU-first reliability)

## What we just set up

- Cross-vendor defaults: CPU-first, GPU optional (`WHISPER_DEVICE=auto`).
- Explicit STT backend switch: `STT_BACKEND=faster-whisper|whisper-cpp`.
- `whisper-cpp` now fails safe: if `whisper-cli`/models aren’t present, it auto-falls back to `faster-whisper`.

## Tomorrow on NVIDIA (work machine)

1) Validate NVIDIA path end-to-end
- Use `STT_BACKEND=faster-whisper`
- Use `WHISPER_DEVICE=cuda` (and set `WHISPER_GPU_DEVICE` as needed)
- Start server and confirm `/health` shows `faster-whisper (CUDA …)`

2) Capture “work machine” baseline config
- Save a working `.env` (or a small snippet in a note) that is known-good for NVIDIA.

3) Performance sanity check
- Confirm STT latency is acceptable with the selected model + compute type.

## Home/AMD follow-ups (later)

- If we want whisper.cpp on AMD: run `scripts/setup_whisper_cpp_hip.sh` + follow `docs/notes/WHISPER_CPP_HIP_SETUP.md`.

## Team contract

- Work machine changes should keep CPU-only fallback working.
- Home machine changes should avoid hardcoding paths and avoid CUDA-only assumptions.
