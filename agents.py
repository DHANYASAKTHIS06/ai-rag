import os, json, re, datetime
from anthropic import Anthropic
from dotenv import load_dotenv
import rag
load_dotenv()
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
_client = None

def llm(system, user, max_tokens=1500):
    global _client
    _client = _client or Anthropic()
    r = _client.messages.create(model=MODEL, max_tokens=max_tokens, system=system,
                                messages=[{"role": "user", "content": user}])
    return "".join(b.text for b in r.content if b.type == "text")

def parse_json(txt, default):
    try:
        return json.loads(re.sub(r"^```(?:json)?|```$", "", txt.strip(), flags=re.M).strip())
    except Exception:
        return default

def fmt(chunks):
    return "\n\n".join(f"[{i+1}] ({c['source']}, p.{c['page']})\n{c['text']}" for i, c in enumerate(chunks))

# ---------- agents ----------
def orchestrator(q):
    out = llm('Classify a student query. Reply ONLY JSON: {"goal":str,"needs_plan":bool,"needs_eligibility":bool}',
              q, 200)
    return parse_json(out, {"goal": q, "needs_plan": True, "needs_eligibility": False})

def knowledge_agent(q, chunks):
    return llm("You answer ONLY from the numbered context. Cite sources like [1]. "
               "If the context lacks the answer, say so plainly. Never invent rules or dates.",
               f"Context:\n{fmt(chunks)}\n\nQuestion: {q}")

def eligibility_agent(q, chunks, profile):
    return llm("Compare the stated eligibility criteria in the context with the student's details. "
               "List: criteria met, criteria not met, and MISSING info. Do NOT declare official "
               "eligibility; advise confirming with the college authority. Cite [n].",
               f"Context:\n{fmt(chunks)}\n\nStudent details: {profile or 'none provided'}\n\nQuestion: {q}")

def planning_agent(q, chunks):
    out = llm('Build an application checklist from the context. Reply ONLY JSON: '
              '{"procedure":str,"documents":[str],"steps":[{"step":str,"deadline":str|null,"source":str}]}. '
              'Use deadlines only if stated in context, else null. source = "file, p.N".',
              f"Context:\n{fmt(chunks)}\n\nGoal: {q}")
    return parse_json(out, {"procedure": q, "documents": [], "steps": []})

def verification_agent(answer, chunks):
    return llm("Fact-check the answer against the context. List any unsupported claims, missing "
               "details, and uncertainties in short bullets. If all supported, say 'Verified against sources.'",
               f"Context:\n{fmt(chunks)}\n\nAnswer:\n{answer}", 500)

def recovery_agent(task, reason, chunks):
    return llm("A student could not complete a step. Suggest a short revised plan (alternatives, who to "
               "contact, extension options) using only the context. Do not mark anything complete.",
               f"Context:\n{fmt(chunks)}\n\nStep: {task['step']} (procedure: {task['procedure']}, "
               f"deadline: {task['deadline']})\nProblem: {reason}\nToday: {datetime.date.today()}")

# ---------- pipeline ----------
def run(q, profile=""):
    trace = []
    def log(agent, detail): trace.append({"agent": agent, "detail": detail})
    plan_info = orchestrator(q); log("Orchestrator", plan_info)
    chunks = rag.search(q, 6); log("Knowledge (retrieval)", f"{len(chunks)} chunks: " +
                                   ", ".join(sorted({f"{c['source']} p.{c['page']}" for c in chunks})))
    if not chunks:
        return {"answer": "No documents indexed yet. Upload college PDFs first.", "trace": trace,
                "plan": None, "eligibility": None, "verification": None, "chunks": []}
    answer = knowledge_agent(q, chunks); log("Knowledge (answer)", "drafted")
    elig = plan = None
    if plan_info.get("needs_eligibility"):
        elig = eligibility_agent(q, chunks, profile); log("Eligibility", "criteria compared")
    if plan_info.get("needs_plan"):
        plan = planning_agent(q, chunks); log("Planning", f"{len(plan.get('steps', []))} steps")
    ver = verification_agent(answer, chunks); log("Verification", ver[:120])
    return {"answer": answer, "eligibility": elig, "plan": plan, "verification": ver,
            "chunks": chunks, "trace": trace}
