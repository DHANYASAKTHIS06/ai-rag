"""
CampusCopilot — Multi-Agent AI Pipeline
Orchestrator → Knowledge → Eligibility → Planning → Verification → Revision → Recovery
Supports: English, Tamil, Hindi, Telugu
Provider: Anthropic Claude (via ANTHROPIC_API_KEY)
"""
import os, json, re, datetime
from dotenv import load_dotenv
import rag

load_dotenv()

MODEL  = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
_anthropic_client = None

# ─── LLM client ─────────────────────────────────────────────────────────────────
def _get_client():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import Anthropic
        key = os.getenv("ANTHROPIC_API_KEY") or _secrets_key()
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured.")
        _anthropic_client = Anthropic(api_key=key)
    return _anthropic_client

def _secrets_key():
    try:
        import streamlit as st
        return st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        return None

def llm(system: str, user: str, max_tokens: int = 1500) -> str:
    try:
        client = _get_client()
        r = client.messages.create(
            model=MODEL, max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in r.content if b.type == "text")
    except Exception as e:
        return f"[AI Error: {e}]"

# ─── helpers ────────────────────────────────────────────────────────────────────
def parse_json(txt: str, default):
    cleaned = re.sub(r"^```(?:json)?\s*|```$", "", txt.strip(), flags=re.M).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        m = re.search(r"(\{.*\}|\[.*\])", cleaned, re.S)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
    return default

def fmt(chunks: list[dict]) -> str:
    """Format retrieved chunks into numbered context block."""
    return "\n\n".join(
        f"[{i+1}] (Source: {c['source']}, Page {c['page']})\n{c['text']}"
        for i, c in enumerate(chunks)
    )

# ─── AGENT 1: Orchestrator ───────────────────────────────────────────────────────
def orchestrator(q: str) -> dict:
    """Classify the query: intent, language, needs_plan, needs_eligibility."""
    system = (
        'You are a query classifier for a university AI assistant. '
        'Classify the student query. Reply ONLY valid JSON:\n'
        '{"goal":str, "needs_plan":bool, "needs_eligibility":bool, '
        '"intent":"general|eligibility|planning|procedure|deadline|scholarship|helpdesk", '
        '"language":"english|tamil|hindi|telugu"}'
    )
    out = llm(system, q, 300)
    return parse_json(out, {
        "goal": q, "needs_plan": True, "needs_eligibility": False,
        "intent": "general", "language": "english"
    })

# ─── AGENT 2: Knowledge Agent ────────────────────────────────────────────────────
def knowledge_agent(q: str, chunks: list[dict], language: str = "english") -> str:
    lang_instruction = {
        "tamil":   "Respond in Tamil language.",
        "hindi":   "Respond in Hindi language.",
        "telugu":  "Respond in Telugu language.",
        "english": "Respond in English.",
    }.get(language, "Respond in English.")

    system = (
        f"You are a helpful university campus assistant. {lang_instruction}\n"
        "Answer ONLY using the numbered context below. "
        "Cite sources using [1], [2], etc. after each relevant statement. "
        "If the context does not contain the answer, say so plainly — never invent facts, "
        "rules, fees, dates, or eligibility criteria."
    )
    return llm(system, f"Context:\n{fmt(chunks)}\n\nQuestion: {q}")

# ─── AGENT 3: Eligibility Agent ──────────────────────────────────────────────────
def eligibility_agent(q: str, chunks: list[dict], profile: str) -> dict:
    system = (
        "You are an eligibility evaluator for university applications. "
        "Compare the eligibility criteria in the context with the student's profile. "
        "Reply ONLY valid JSON:\n"
        '{"met":["criterion..."], "not_met":["criterion..."], "missing":["info needed..."], '
        '"summary":"brief overall assessment", "can_apply":bool}\n'
        "met = criteria the student satisfies. "
        "not_met = criteria the student clearly does not meet. "
        "missing = information not provided by student needed to evaluate. "
        "can_apply = true ONLY if ALL mandatory criteria in context are met. "
        "NEVER declare full eligibility if mandatory criteria remain unchecked. "
        "Always cite [n] after each point."
    )
    out = llm(system,
              f"Context:\n{fmt(chunks)}\n\nStudent profile: {profile or 'not provided'}\n\nQuery: {q}")
    return parse_json(out, {
        "met": [], "not_met": [], "missing": ["Student profile not provided"],
        "summary": "Unable to evaluate — provide your profile details.",
        "can_apply": False
    })

# ─── AGENT 4: Planning Agent ─────────────────────────────────────────────────────
def planning_agent(q: str, chunks: list[dict]) -> dict:
    system = (
        'Build an application checklist from the context. Reply ONLY valid JSON:\n'
        '{"procedure":str, "documents":[str], '
        '"steps":[{"step":str,"deadline":str|null,"source":str}]}\n'
        'Use deadline values ONLY if explicitly stated in context, else null. '
        'source = "filename, p.N". Keep steps concise and actionable.'
    )
    out = llm(system, f"Context:\n{fmt(chunks)}\n\nGoal: {q}")
    return parse_json(out, {"procedure": q, "documents": [], "steps": []})

# ─── AGENT 5: Verification Agent ─────────────────────────────────────────────────
def verification_agent(answer: str, chunks: list[dict]) -> dict:
    system = (
        "Fact-check the answer against the context. "
        "Check: dates, fees, numerical values, eligibility criteria, citation accuracy, "
        "unsupported claims. Reply ONLY valid JSON:\n"
        '{"verified":bool, "issues":["issue..."], "summary":"short summary"}\n'
        'verified=true means ALL claims are supported by context. '
        'List every specific unsupported or potentially wrong claim in issues[].'
    )
    out = llm(system, f"Context:\n{fmt(chunks)}\n\nAnswer:\n{answer}", 600)
    return parse_json(out, {
        "verified": True, "issues": [],
        "summary": "Verification completed."
    })

# ─── AGENT 6: Revision Agent ─────────────────────────────────────────────────────
def revision_agent(original_answer: str, chunks: list[dict], issues: list[str]) -> str:
    system = (
        "You are a revision agent. The original answer had the following issues identified by "
        "a fact-checker. Rewrite the answer to fix these specific issues using only the context. "
        "Keep citations [n]. Do not add information not in the context."
    )
    issues_txt = "\n".join(f"- {i}" for i in issues)
    return llm(system,
               f"Context:\n{fmt(chunks)}\n\nOriginal answer:\n{original_answer}\n\n"
               f"Issues to fix:\n{issues_txt}")

# ─── AGENT 7: Recovery Agent ─────────────────────────────────────────────────────
def recovery_agent(task: dict, reason: str, chunks: list[dict]) -> str:
    system = (
        "A student could not complete a university application step. "
        "Suggest a short revised plan: alternatives, who to contact, extension options, "
        "using ONLY information from the context. Do NOT mark anything as complete."
    )
    return llm(system,
               f"Context:\n{fmt(chunks)}\n\n"
               f"Step: {task.get('step')} (Procedure: {task.get('procedure')}, "
               f"Deadline: {task.get('deadline')})\n"
               f"Problem: {reason}\nToday: {datetime.date.today()}")

# ─── AGENT 8: Helpdesk Agent ─────────────────────────────────────────────────────
def helpdesk_agent(subject: str, description: str, chunks: list[dict]) -> str:
    system = (
        "You are a university helpdesk assistant. Generate a professional, empathetic, "
        "and accurate response to a student's support ticket using ONLY the context provided. "
        "Cite [n] where relevant. Keep the response concise and actionable. "
        "If the context does not contain enough information, acknowledge that and direct the "
        "student to the relevant department."
    )
    ctx = fmt(chunks) if chunks else "No relevant documents found in knowledge base."
    return llm(system,
               f"Context:\n{ctx}\n\nTicket Subject: {subject}\nTicket Description: {description}",
               800)

# ─── AGENT 9: Application Letter Agent ──────────────────────────────────────────
def application_letter_agent(letter_type: str, student_info: dict,
                              recipient_info: dict, subject: str, details: str) -> str:
    system = (
        "You are a professional letter writer for university applications. "
        "Write a formal, polite, and complete application letter. "
        "Format: Date, From address, To address, Subject line, Salutation, "
        "Body paragraphs, Closing, Signature. "
        "Use proper formal English. Do not add information not provided."
    )
    prompt = (
        f"Letter type: {letter_type}\n\n"
        f"Student info:\n{json.dumps(student_info, indent=2)}\n\n"
        f"Recipient info:\n{json.dumps(recipient_info, indent=2)}\n\n"
        f"Subject: {subject}\n\n"
        f"Additional details / body content:\n{details}"
    )
    return llm(system, prompt, 1200)

# ─── Main Pipeline ───────────────────────────────────────────────────────────────
def run(q: str, profile: str = "", user_id=None) -> dict:
    """
    Full multi-agent pipeline.
    Returns: {answer, eligibility, plan, verification, chunks, trace, language, intent, error}
    """
    trace = []
    def log(agent, detail):
        trace.append({"agent": agent, "detail": str(detail)})

    # 1. Orchestrator
    try:
        plan_info = orchestrator(q)
    except Exception as e:
        plan_info = {"goal": q, "needs_plan": True, "needs_eligibility": False,
                     "intent": "general", "language": "english"}
        log("Orchestrator", f"Error: {e}")
    log("Orchestrator", plan_info)
    language = plan_info.get("language", "english")
    intent   = plan_info.get("intent", "general")

    # 2. Retrieval
    try:
        chunks = rag.search(q, 6)
    except Exception as e:
        chunks = []
        log("Retrieval", f"Error: {e}")
    log("Retrieval", f"{len(chunks)} chunks from: " +
        ", ".join(sorted({f"{c['source']} p.{c['page']}" for c in chunks})))

    if not chunks:
        return {
            "answer": (
                "⚠️ No documents are indexed yet. "
                "Please ask an administrator to upload and index college documents first."
            ),
            "eligibility": None, "plan": None,
            "verification": {"verified": True, "issues": [], "summary": "No documents."},
            "chunks": [], "trace": trace,
            "language": language, "intent": intent,
        }

    # 3. Knowledge agent
    answer = knowledge_agent(q, chunks, language)
    log("Knowledge Agent", "Answer drafted")

    # 4. Eligibility agent (conditional)
    elig = None
    if plan_info.get("needs_eligibility") or intent == "eligibility":
        try:
            elig = eligibility_agent(q, chunks, profile)
            log("Eligibility Agent", f"met={len(elig.get('met',[]))}, "
                                     f"not_met={len(elig.get('not_met',[]))}")
        except Exception as e:
            log("Eligibility Agent", f"Error: {e}")

    # 5. Planning agent (conditional)
    plan = None
    if plan_info.get("needs_plan") or intent in ("planning", "procedure"):
        try:
            plan = planning_agent(q, chunks)
            log("Planning Agent", f"{len(plan.get('steps', []))} steps")
        except Exception as e:
            log("Planning Agent", f"Error: {e}")

    # 6. Verification
    ver = {"verified": True, "issues": [], "summary": "Verification skipped."}
    try:
        ver = verification_agent(answer, chunks)
        log("Verification Agent", ver.get("summary", ""))
    except Exception as e:
        log("Verification Agent", f"Error: {e}")

    # 7. Revision (if issues found)
    if not ver.get("verified", True) and ver.get("issues"):
        try:
            revised = revision_agent(answer, chunks, ver["issues"])
            answer  = revised
            log("Revision Agent", f"Answer revised — {len(ver['issues'])} issue(s) addressed")
        except Exception as e:
            log("Revision Agent", f"Error: {e}")

    return {
        "answer":       answer,
        "eligibility":  elig,
        "plan":         plan,
        "verification": ver,
        "chunks":       chunks,
        "trace":        trace,
        "language":     language,
        "intent":       intent,
    }
