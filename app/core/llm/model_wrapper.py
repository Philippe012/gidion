"""
Thin wrapper around llama-cpp-python (SDLC Phase 2.2). Keeps the rest
of the codebase from depending on llama_cpp directly, so the model
backend can be swapped without touching prompts.py or guardrails.py.
"""

from app import config


class ModelUnavailableError(RuntimeError):
    """Raised when the GGUF model file isn't present. Phase 5.4's
    first-run check should catch this before the user ever gets here,
    but callers (e.g. app/ui/server.py) should handle it gracefully in
    case the model was deleted/moved after first run."""


class LocalModel:
    def __init__(self):
        self._llm = None  # lazy-loaded

    def _ensure_loaded(self):
        if self._llm is not None:
            return
        if not config.LLM_MODEL_PATH.exists():
            raise ModelUnavailableError(
                f"Model file not found at {config.LLM_MODEL_PATH}. "
                f"Download a GGUF model (see README) and place it in "
                f"{config.MODELS_DIR}, or set GIDION_LLM_MODEL to its "
                f"filename."
            )
        try:
            from llama_cpp import Llama
        except ImportError as exc:
            raise ModelUnavailableError(
                "llama-cpp-python is not installed. Run: "
                "pip install llama-cpp-python"
            ) from exc

        self._llm = Llama(
            model_path=str(config.LLM_MODEL_PATH),
            n_ctx=config.LLM_CONTEXT_SIZE,
            verbose=False,
        )

    def generate(self, prompt: str, max_tokens: int | None = None) -> str:
        """Returns the model's raw text completion. Callers are
        responsible for running the result through
        core/llm/guardrails.py before displaying or speaking it."""
        self._ensure_loaded()
        result = self._llm(
            prompt,
            max_tokens=max_tokens or config.LLM_MAX_NEW_TOKENS,
            temperature=config.LLM_TEMPERATURE,
            stop=["\n\n\n"],
        )
        return result["choices"][0]["text"].strip()