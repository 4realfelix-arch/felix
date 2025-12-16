# whisper.cpp HIP (AMD/ROCm) setup

This repo supports `STT_BACKEND=whisper-cpp`, which uses a locally built `whisper-cli` binary plus GGML model files.

## Prereqs

- ROCm installed and working (optional but required for HIP acceleration)
- Build tools: `git`, `cmake`, a C/C++ compiler

Quick ROCm sanity check:

```bash
rocm-smi
/opt/rocm/bin/rocminfo | head
```

## Build

Run the helper:

```bash
bash scripts/setup_whisper_cpp_hip.sh
```

This creates:
- `whisper.cpp/build/bin/whisper-cli`

## Download a model

From the `whisper.cpp` folder:

```bash
cd whisper.cpp
bash ./models/download-ggml-model.sh large-v3-turbo
```

That should place a file like:
- `whisper.cpp/models/ggml-large-v3-turbo.bin`

## Configure Felix

In `.env`:

```env
STT_BACKEND=whisper-cpp
WHISPER_MODEL=ggml-large-v3-turbo.bin
WHISPER_GPU_DEVICE=1
```

Notes:
- `WHISPER_GPU_DEVICE` is used as `HIP_VISIBLE_DEVICES` by the wrapper.
- If `whisper-cli` or the model file is missing, Felix will automatically fall back to `faster-whisper`.
