#!/usr/bin/env bash
set -euo pipefail

echo "[Gidion build] Installing dependencies..."
pip install -r requirements.txt

echo "[Gidion build] Running tests before packaging..."
pytest tests/ -v

echo "[Gidion build] Checking that model files are actually present to bundle..."
missing=0
for f in \
  "models/phi-3-mini-4k-instruct-q4.gguf" \
  "models/ggml-base.bin" \
  "models/piper/en_US-default.onnx" \
  "models/voice_clone/reference.wav"
do
  if [ ! -f "$f" ]; then
    echo "  MISSING: $f"
    missing=1
  fi
done
if [ "$missing" -eq 1 ]; then
  echo "[Gidion build] Model files missing. Add them before continuing."
  exit 1
fi

echo "[Gidion build] Building with PyInstaller (--onedir)..."
pyinstaller --onedir --noconfirm \
  --name gidion \
  --add-data "docs:docs" \
  --add-data "models:models" \
  --add-data "app/ui/templates:app/ui/templates" \
  --add-data "app/ui/static:app/ui/static" \
  --add-data "assets:assets" \
  --collect-all torch \
  --collect-all transformers \
  --collect-all TTS \
  --collect-all torchcodec \
  --collect-all piper \
  --collect-all pywhispercpp \
  --collect-all llama_cpp \
  --collect-all espeakng_loader \
  --collect-all librosa \
  desktop.py

echo "[Gidion build] Done. Folder build is in dist/gidion/"