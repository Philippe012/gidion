@echo off
REM Packaging script (SDLC Phase 5.1) - Windows-native version of build.sh.
REM --onedir instead of --onefile: a --onefile build of a 5-10GB app would
REM re-extract everything into a temp folder on EVERY launch. --onedir
REM installs once, starts fast.

echo [Gidion build] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 goto :error

echo [Gidion build] Running tests before packaging...
python -m pytest tests/ -v
if errorlevel 1 goto :error

echo [Gidion build] Checking that model files are present to bundle...
set MISSING=0
if not exist "models\phi-3-mini-4k-instruct-q4.gguf" (echo   MISSING: models\phi-3-mini-4k-instruct-q4.gguf & set MISSING=1)
if not exist "models\ggml-base.bin" (echo   MISSING: models\ggml-base.bin & set MISSING=1)
if not exist "models\piper\en_US-default.onnx" (echo   MISSING: models\piper\en_US-default.onnx & set MISSING=1)
if not exist "models\voice_clone\reference.wav" (echo   MISSING: models\voice_clone\reference.wav & set MISSING=1)
if "%MISSING%"=="1" (
    echo [Gidion build] One or more model files are missing above.
    echo   This build ships everything bundled, so the installer would
    echo   be incomplete without them.
    goto :error
)

echo [Gidion build] Building with PyInstaller (--onedir)...
pyinstaller --onedir ^
  --name gidion ^
  --add-data "docs;docs" ^
  --add-data "models;models" ^
  --collect-all torch ^
  --collect-all transformers ^
  --collect-all TTS ^
  --collect-all torchcodec ^
  --collect-all piper ^
  --collect-all pywhispercpp ^
  --collect-all llama_cpp ^
  --collect-all espeakng_loader ^
  --collect-all librosa ^
  run_gidion.py
if errorlevel 1 goto :error

echo [Gidion build] Done. Folder build is in dist\gidion\
echo [Gidion build] IMPORTANT: test dist\gidion\gidion.exe on a clean
echo   machine or VM WITHOUT this dev venv installed.
echo [Gidion build] Next: wrap dist\gidion\ with Inno Setup - see
echo   gidion_installer.iss
goto :eof

:error
echo [Gidion build] FAILED - see the error above.
exit /b 1