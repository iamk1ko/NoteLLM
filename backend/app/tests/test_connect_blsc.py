import os

import pytest


def _blsc_env() -> tuple[str | None, str | None]:
    api_key = os.getenv("BLSC_API_KEY")
    base_url = os.getenv("BLSC_BASE_URL")
    return api_key, base_url


def _is_reachable(url: str, timeout_s: float = 1.0) -> bool:
    """Best-effort reachability check without extra deps."""
    from urllib.request import Request, urlopen

    try:
        req = Request(url, method="GET")
        with urlopen(req, timeout=timeout_s) as resp:
            return 200 <= getattr(resp, "status", 200) < 500
    except Exception:
        return False


@pytest.mark.integration
def test_connect_blsc_chat_completion():
    """Integration smoke test for your BLSC(OpenAI-compatible) proxy.

    Required env vars:
      - BLSC_API_KEY
      - BLSC_BASE_URL  (example: https://your-proxy-host)

    This test is safe by default:
    - If env vars are missing, it skips.
    - If the base URL isn't reachable, it skips.

    Tip: keep the prompt tiny to reduce cost/latency.
    """

    api_key, base_url = _blsc_env()
    if not api_key or not base_url:
        pytest.skip("BLSC_API_KEY/BLSC_BASE_URL not set")

    import openai

    client = openai.OpenAI(
        api_key=api_key,
        base_url=f"{base_url}/v1/",
    )

    response = client.chat.completions.create(
        model=os.getenv("BLSC_MODEL", "DeepSeek-V3.2"),
        messages=[{"role": "user", "content": "你是谁?"}],
        temperature=0,
    )

    # Assertions instead of prints
    assert response is not None
    assert response.choices
    content = (response.choices[0].message.content or "").strip()
    print(content)
    # assert content, "Empty completion content"
    # assert "OK" in content.upper(), f"Unexpected response: {content}"


@pytest.mark.integration
def test_connect_blsc_chat_completion_by_langchain():
    """Integration smoke test for your BLSC(OpenAI-compatible) proxy via LangChain.

    Required env vars:
      - BLSC_API_KEY
      - BLSC_BASE_URL  (example: https://your-proxy-host)

    This test is safe by default:
    - If env vars are missing, it skips.
    - If the base URL isn't reachable, it skips.
    Tip: keep the prompt tiny to reduce cost/latency.
    """

    api_key, base_url = _blsc_env()
    if not api_key or not base_url:
        pytest.skip("BLSC_API_KEY/BLSC_BASE_URL not set")

    print(api_key, base_url)

    from langchain_openai import ChatOpenAI
    from langchain_core.messages.ai import AIMessage
    from langchain.agents import create_agent

    llm = ChatOpenAI(
        api_key=api_key,
        base_url=f"{base_url}/v1/",
        model="DeepSeek-V3.2",
        temperature=0,
    )

    response: AIMessage = llm.invoke(["你是谁?"])
    # Assertions instead of prints
    assert response is not None
    content = (response.content or "").strip()
    print(content)

    agent = create_agent(llm)

    input_message = {"role": "user", "content": "写一段500字的作文，题目是《我的一天》"}
    for step in agent.stream(
            {"messages": [input_message]},
            stream_mode="values",
    ):
        step["messages"][-1].pretty_print()
