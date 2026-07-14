set -euo pipefail

echo "[Gidion build] Installing dependencies..."
pip install -r requirements.txt

echo "[Gidion build] Running tests before packaging..."
pytest tests/ -v

echo "[Gidion build] Building single-file executable with PyInstaller..."
pyinstaller --onefile \
  --name gidion \
  --add-data "docs:docs" \
  app/main.py

echo "[Gidion build] Done. Executable is in dist/gidion"
echo "[Gidion build] NOTE (Phase 5.2): the GGUF model is not bundled by"
echo "  default due to size. Either:"
echo "    (a) copy a model into models/ before building and add"
echo "        --add-data \"models:models\" above, or"
echo "    (b) ship without it and let main.py's first-run check guide"
echo "        the user to download one (models/README or Hugging Face)."