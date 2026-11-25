"""
CampusCopilot — LLM module (backward compatibility wrapper)
Delegates to agents.llm()
"""
import agents

def ask(system: str, user: str, max_tokens: int = 1500) -> str:
    return agents.llm(system, user, max_tokens)

def ask_json(system: str, user: str, default=None):
    import json, re
    text = ask(system + "\nReturn ONLY valid JSON. No prose, no markdown fences.", user)
    text = re.sub(r"^```(?:json)?\s*|```$", "", text.strip(), flags=re.M).strip()
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
