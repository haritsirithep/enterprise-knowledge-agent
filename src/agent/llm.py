"""Thin wrapper over LiteLLM so any provider works: gemini/, openai/, anthropic/, ollama/ ..."""
import json
import re

import litellm

from .config import settings

litellm.suppress_debug_info = True


def provider(model: str) -> str:
    return model.split("/", 1)[0]


def complete_json(prompt: str, model: str, system: str = "", api_key: str | None = None) -> tuple[dict, str]:
    """Return (parsed JSON, model that actually answered — may be a fallback model).

    api_key: optional key typed by the user in the UI. If empty, LiteLLM reads it from .env.
    """
    messages = [{"role": "system", "content": system}] if system else []
    messages.append({"role": "user", "content": prompt})
    # temperature=0 for repeatable answers. Gemini 3+ is deprecating sampling params, so we skip it there.
    extra = {} if model.startswith("gemini/") else {"temperature": 0}
    fallbacks = [m for m in settings.fallback_models if m != model]
    if api_key:
        extra["api_key"] = api_key
        # A user's key belongs to one provider. Never send it to another provider's fallback.
        fallbacks = [m for m in fallbacks if provider(m) == provider(model)]
    response = litellm.completion(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        timeout=settings.llm_timeout_s,  # never let one call hang the UI
        num_retries=1,
        # If this model is down or overloaded, try the next one instead of failing.
        fallbacks=fallbacks,
        **extra,
    )
    return parse_json(response.choices[0].message.content), response.model


def parse_json(text: str) -> dict:
    """Models sometimes wrap JSON in ```json fences. Grab the first {...} block."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(match.group(0) if match else text)
