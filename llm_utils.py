"""Shared LLM call utilities with error handling."""

import json
import re
import time
from groq import Groq
from config import GROQ_API_KEY, FALLBACK_MODELS

_client = None


def get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def _try_call(client, model: str, system: str, user_msg: str, max_tokens: int, temperature: float) -> dict:
    """Single attempt to call LLM with json_object mode + fallbacks."""
    try:
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

    except Exception as e:
        error_str = str(e)

        # If Groq rejected the JSON but gave us failed_generation, extract it
        if "failed_generation" in error_str:
            extracted = _extract_json_from_error(error_str)
            if extracted is not None:
                return extracted

        # If rate limit, propagate so caller can try fallback
        if "rate_limit" in error_str or "429" in error_str:
            raise

        # Retry without json_object mode
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
                temperature=temperature,
            )
            text = response.choices[0].message.content
            return _extract_json_from_text(text)
        except Exception:
            raise e


def call_llm_json(model: str, system: str, user_msg: str, max_tokens: int = 4096, temperature: float = 0.3) -> dict:
    """Call LLM and return parsed JSON. Auto-fallback to other models on rate limit."""
    client = get_client()

    # Try primary model
    saved_err = None
    try:
        return _try_call(client, model, system, user_msg, max_tokens, temperature)
    except Exception as e:
        if "rate_limit" not in str(e) and "429" not in str(e):
            raise
        saved_err = e

    # Primary hit rate limit — try fallbacks
    print(f"  Rate limit on {model}, trying fallbacks...")
    for fallback in FALLBACK_MODELS:
        if fallback == model:
            continue
        try:
            time.sleep(1)
            result = _try_call(client, fallback, system, user_msg, max_tokens, temperature)
            print(f"  Using fallback: {fallback}")
            return result
        except Exception as fb_err:
            if "rate_limit" in str(fb_err) or "429" in str(fb_err):
                continue
            raise

    raise saved_err


def _fix_malformed_json(raw: str) -> str:
    """Try to fix common JSON issues from weak models (missing quotes, etc.)."""
    # Fix unquoted string values: "key": value without quotes
    # Pattern: "key": followed by text that isn't a quote, number, bool, null, [ or {
    fixed = re.sub(
        r'("(?:explanation|cultural_context|transcript_excerpt|definition|context_meaning|gloss|usage_context|example|why_rich_point|misuse_consequence|origin_story|when_to_use|outsider_rephrase|msg)":\s*)([A-Za-z][^,\n}]*?)(\s*[,\n}])',
        lambda m: m.group(1) + '"' + m.group(2).replace('"', '\\"').strip() + '"' + m.group(3),
        raw
    )
    # Fix empty values: "key": followed by comma or }
    fixed = re.sub(r'("[\w_]+":\s*)(,|\})', r'\1""\2', fixed)
    return fixed


def _extract_json_from_error(error_str: str) -> dict:
    """Try to extract valid JSON from Groq's failed_generation error message."""
    try:
        # Find the failed_generation content
        match = re.search(r"'failed_generation':\s*'(.*?)'}\s*}", error_str, re.DOTALL)
        if not match:
            return None

        raw = match.group(1)
        # Unescape
        raw = raw.replace("\\'", "'").replace("\\n", "\n")

        # Try parsing as-is
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Try fixing malformed JSON (missing quotes from weak models)
        try:
            fixed = _fix_malformed_json(raw)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # Try wrapping in object brackets
        try:
            return json.loads("{" + raw + "}")
        except json.JSONDecodeError:
            pass

        try:
            fixed = _fix_malformed_json("{" + raw + "}")
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

    except Exception:
        pass
    return None


def _extract_json_from_text(text: str) -> dict:
    """Extract JSON from text that may contain markdown code blocks."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from code block
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding first { ... } block
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract JSON from response: {text[:200]}")
