#!/usr/bin/env bash
set -euo pipefail

# Builds whisper.cpp with HIP/ROCm (AMD) support.
# This is intentionally conservative and may need tweaks per distro/ROCm version.
#
# Output:
# - ./whisper.cpp/build/bin/whisper-cli
# - ./whisper.cpp/models/<ggml-*.bin>

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WHISPER_DIR="$REPO_ROOT/whisper.cpp"

echo "== whisper.cpp HIP setup =="
echo "Repo root: $REPO_ROOT"

if ! command -v cmake >/dev/null 2>&1; then
  echo "ERROR: cmake not found. Install it first (e.g. apt/yum/pacman)." >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git not found. Install it first." >&2
  exit 1
fi

# ROCm sanity checks (non-fatal)
if command -v rocm-smi >/dev/null 2>&1; then
  echo "ROCm detected: rocm-smi present"
else
  echo "NOTE: rocm-smi not found; ensure ROCm is installed and on PATH if you want HIP acceleration."
fi

if [[ ! -d "$WHISPER_DIR" ]]; then
  echo "Cloning whisper.cpp into $WHISPER_DIR"
  git clone https://github.com/ggerganov/whisper.cpp.git "$WHISPER_DIR"
else
  echo "Using existing $WHISPER_DIR"
fi

cd "$WHISPER_DIR"

echo "Updating submodules (if any)"
git submodule update --init --recursive

echo "Configuring build (HIP)"
mkdir -p build
cmake -S . -B build -DGGML_HIP=ON -DCMAKE_BUILD_TYPE=Release

echo "Building"
cmake --build build -j

if [[ -x "$WHISPER_DIR/build/bin/whisper-cli" ]]; then
  echo "OK: built whisper-cli at $WHISPER_DIR/build/bin/whisper-cli"
else
  echo "ERROR: whisper-cli not found after build. Check build output." >&2
  exit 1
fi

echo "\nNext: download a GGML model into whisper.cpp/models"
echo "Example (pick a model you want):"
echo "  cd $WHISPER_DIR"
echo "  bash ./models/download-ggml-model.sh large-v3-turbo"
echo "\nThen set in .env:"
echo "  STT_BACKEND=whisper-cpp"
echo "  WHISPER_MODEL=ggml-large-v3-turbo.bin"
