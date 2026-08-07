import re
import threading
from pathlib import Path
from app import config

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None


class ModelUnavailableError(Exception):
    pass


class LocalModel:
    """
    Thread-safe wrapper around llama-cpp-python.
    """

    def __init__(self):
        self.model = None
        self._lock = threading.Lock()
        self._ensure_loaded()

    def _ensure_loaded(self):
        if self.model is not None:
            return

        if Llama is None:
            raise ModelUnavailableError("llama-cpp-python is not installed.")

        # Find model
        model_path = getattr(config, 'LLM_MODEL_PATH', None)
        if not model_path or not Path(model_path).exists():
            models_dir = Path("models")
            if models_dir.exists():
                ggufs = list(models_dir.glob("*.gguf"))
                if ggufs:
                    model_path = str(ggufs[0])

        if not model_path or not Path(model_path).exists():
            raise ModelUnavailableError(f"No .gguf model found. Checked: {model_path or 'models/*.gguf'}")

        n_ctx = getattr(config, 'LLM_CONTEXT_SIZE', 2048)
        print(f"[LLM] Loading {model_path} (n_ctx={n_ctx})...")

        self.model = Llama(
            model_path=str(model_path),
            n_ctx=n_ctx,
            n_batch=min(512, n_ctx // 2),
            verbose=False,
            n_gpu_layers=getattr(config, 'LLM_N_GPU_LAYERS', 0)
        )
        print("[LLM] Model loaded successfully.")

    def generate(self, prompt: str, max_tokens: int = 120, temperature: float = 0.3) -> str:
        if self.model is None:
            return ""

        with self._lock:
            try:
                max_chars = getattr(config, 'LLM_CONTEXT_SIZE', 2048) * 3
                if len(prompt) > max_chars:
                    prompt = prompt[:max_chars] + "\n...[truncated]\n"

                # Phi-3-mini-4k-instruct requires chat tokens
                formatted = f"<|user|>\n{prompt}<|end|>\n<|assistant|>\n"

                output = self.model(
                    formatted,
                    max_tokens=getattr(config, "LLM_MAX_NEW_TOKENS", max_tokens),
                    temperature=getattr(config, "LLM_TEMPERATURE", temperature),
                    stop=["<|end|>", "<|user|>", "<|system|>", "\nUser:", "\nGidion:"],
                    echo=False
                )

                # defensive parsing / logging
                text = ""
                if isinstance(output, dict):
                    choices = output.get("choices")
                    if isinstance(choices, list) and choices:
                        first = choices[0]
                        text = first.get("text", "") or ""
                    else:
                        print(f"[LLM] Unexpected response shape (no choices): {type(output)} -> {output}")
                        text = str(output)
                else:
                    text = str(output or "")

                text = re.sub(r'^\s*Answer\s*=\s*', '', text, flags=re.I)
                text = re.sub(r'^\s*(assistant|user|gidion)\s*[:=-]+\s*', '', text, flags=re.I)
                text = text.strip()

                # --- sanitiser: strip leading greetings/apologies ---
                text = re.sub(r'^(hello|hi|hey)[\s\!\.,:-]*', '', text, flags=re.I).strip()
                text = re.sub(r"^i('?m| am) gidion[^\n]*\n?", "", text, flags=re.I).strip()
                text = re.sub(r"^(i[' ]?m|i am) sorry[^\n]*\n?", "", text, flags=re.I).strip()

                # If this was a "next question" prompt, keep only the first sentence/question.
                if "The rules engine needs this piece of information next:" in prompt:
                    # keep up to the first '?' or final '.' if no question mark
                    q_match = re.search(r"([^\n\?\.]+[\?\.])", text)
                    if q_match:
                        text = q_match.group(1).strip()

                # NOTE: guardrails.scan_output() / safe_or_fallback() should still be
                # invoked by the caller after generate() returns, so banned patterns
                # are enforced even after this sanitiser runs. It is not called here
                # because guardrails isn't imported/wired into this module in the
                # snippet provided — wire it in at the call site or import it above
                # if you want it enforced inside generate() itself.

                return text

            except Exception as e:
                print(f"[LLM] Generation failed (safe catch): {e}")
                return ""
            