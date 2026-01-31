import os
import time
from typing import Optional

import pytest


def _ollama_base_url() -> str:
    # Ollama default: http://127.0.0.1:11434
    return os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")


def _can_connect(base_url: str, timeout_s: float = 1.0) -> bool:
    """Best-effort local connectivity check without adding extra deps.

    We use stdlib urllib so we don't need requests/httpx.
    """
    from urllib.request import urlopen

    try:
        with urlopen(f"{base_url}/api/tags", timeout=timeout_s) as resp:
            return 200 <= getattr(resp, "status", 200) < 300
    except Exception:
        return False


def _has_model(base_url: str, model: str, timeout_s: float = 2.0) -> Optional[bool]:
    """Returns True/False if we can determine presence, or None if unknown."""
    import json
    from urllib.request import urlopen

    try:
        with urlopen(f"{base_url}/api/tags", timeout=timeout_s) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        models = payload.get("models") or []
        names = {m.get("name") for m in models if isinstance(m, dict)}
        # Ollama sometimes returns name like 'qwen3:0.6b'
        return model in names
    except Exception:
        return None


@pytest.mark.integration
def test_langchain_ollama_chat_qwen3_smoke():
    """Smoke test: send a tiny prompt to local Ollama model.

    This is intentionally small and defensive:
    - Skips if Ollama isn't running.
    - Skips if the model isn't pulled.

    Set env:
      - OLLAMA_BASE_URL (optional)
    """

    base_url = _ollama_base_url()

    if not _can_connect(base_url):
        pytest.skip(f"Ollama not reachable at {base_url}. Start it and retry.")

    model = os.getenv("OLLAMA_MODEL", "qwen3:0.6b")
    has_model = _has_model(base_url, model)
    if has_model is False:
        pytest.skip(
            f"Model '{model}' not found in Ollama at {base_url}. "
            f"Pull it first (e.g. `ollama pull {model}`)."
        )

    # Import only after preflight so missing deps fail loudly in the right place.
    from langchain_ollama import ChatOllama

    llm = ChatOllama(
        model=model,
        base_url=base_url,
        temperature=0,
    )

    prompt = "Reply with exactly: OK"

    start = time.time()
    message = llm.invoke(prompt)
    elapsed = time.time() - start

    # LangChain message has .content
    content = (getattr(message, "content", "") or "").strip()

    assert content, "The model returned empty content"
    assert "OK" in content.upper(), f"Unexpected model output: {content}"

    # Keep this generous for first-run warmup.
    assert elapsed < 60, f"Model call too slow ({elapsed:.1f}s)."
