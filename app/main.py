
import sys

from app import config


def check_model_present() -> bool:
    if config.LLM_MODEL_PATH.exists():
        return True
    print(
        f"[Gidion] No language model found at {config.LLM_MODEL_PATH}.\n"
        f"The rules engine and UI will still work — you'll just get "
        f"plain classification text instead of LLM-phrased notes.\n"
        f"To enable note-writing, download a GGUF model (see README.md) "
        f"and place it in {config.MODELS_DIR}.",
        file=sys.stderr,
    )
    return False


def main():
    check_model_present()
    from app.ui import server
    print(f"[Gidion] Starting local UI at http://{config.UI_HOST}:{config.UI_PORT}")
    print(f"[Gidion] {config.DISCLAIMER_TEXT}")
    server.run()


if __name__ == "__main__":
    main()