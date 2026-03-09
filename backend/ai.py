"""
AI client dispatch.

call_ai() abstracts over Anthropic, OpenAI-compatible, and Ollama endpoints.
Raises on API errors — callers handle and return appropriate HTTP responses.
"""

import anthropic


def call_ai(
    endpoint: str,
    system_prompt: str,
    messages: list[dict],
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> str:
    """Call the configured AI endpoint. Returns the response text.

    endpoint: 'anthropic' | 'openai' | 'ollama'
    messages: list of {role, content} dicts (no system message — pass system_prompt separately)
    """
    if endpoint in ("openai", "ollama", "local"):
        from openai import OpenAI
        defaults = {
            "local":  ("http://localhost:5052/v1", "Qwen/Qwen2.5-7B-Instruct", api_key or "local"),
            "ollama": ("http://localhost:11434/v1", "qwen2.5:7b", api_key or "ollama"),
            "openai": ("https://api.openai.com/v1", "gpt-4o-mini", api_key),
        }
        default_base, default_model, oa_key = defaults[endpoint]
        client = OpenAI(api_key=oa_key, base_url=base_url or default_base)
        response = client.chat.completions.create(
            model=model or default_model,
            max_tokens=2048,
            messages=[{"role": "system", "content": system_prompt}] + messages,
        )
        return response.choices[0].message.content or ""
    else:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model or "claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text
