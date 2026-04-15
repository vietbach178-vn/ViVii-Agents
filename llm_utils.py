"""Minimal LLM call utility for the joke pipeline. Groq-based, JSON mode with fallbacks."""

import json
import re
import time

from groq import Groq

from config import FALLBACK_MODELS, GROQ_API_KEY

_client = None


def get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def _extract_json_from_text(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not extract JSON from response: {text[:200]}")


def _one_call(client, model, system, user_msg, max_tokens, temperature):
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        response_format={"type": "json_object"},
        temperature=temperature,
    )
    return json.loads(response.choices[0].message.content)


def call_llm_json(
    model: str,
    system: str,
    user_msg: str,
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> dict:
    """Call LLM and return parsed JSON. Falls back on rate-limit errors."""
    client = get_client()
    try:
        return _one_call(client, model, system, user_msg, max_tokens, temperature)
    except Exception as e:
        err = str(e)
        if "rate_limit" not in err and "429" not in err:
            try:
                return _one_call(
                    client, model, system, user_msg, max_tokens, temperature
                )
            except Exception:
                raise

    for fb in FALLBACK_MODELS:
        if fb == model:
            continue
        try:
            time.sleep(1)
            return _one_call(client, fb, system, user_msg, max_tokens, temperature)
        except Exception as fb_err:
            if "rate_limit" in str(fb_err) or "429" in str(fb_err):
                continue
            raise
    raise RuntimeError("All models rate-limited")
