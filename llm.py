import os, json, re
import anthropic

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

def _client():
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("ANTHROPIC_API_KEY")
        except Exception:
            pass
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")
    return anthropic.Anthropic(api_key=key)

def ask(system: str, user: str, max_tokens: int = 1500) -> str:
    r = _client().messages.create(
        model=MODEL, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": user}])
    return "".join(b.text for b in r.content if b.type == "text")

def ask_json(system: str, user: str, default=None):
    """Ask for JSON only and parse defensively."""
    text = ask(system + "\nReturn ONLY valid JSON. No prose, no markdown fences.", user)
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"(\{.*\}|\[.*\])", text, re.S)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
    return default
