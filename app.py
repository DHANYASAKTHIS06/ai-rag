try:  # needed on Streamlit Cloud (old system sqlite)
    __import__("pysqlite3"); import sys; sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except Exception:
    pass
import os, datetime, streamlit as st
if "ANTHROPIC_API_KEY" in st.secrets if hasattr(st, "secrets") and os.path.exists(".streamlit/secrets.toml") else False:
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
import db, rag, agents

st.set_page_config(page_title="CampusCopilot", page_icon="🎓", layout="wide")
db.init()
st.title("🎓 CampusCopilot")
st.caption("Campus assistant: cited answers, checklists, tracking and change detection. "
           "Always confirm final decisions with the official college authority.")

# ---------- sidebar: upload ----------
with st.sidebar:
    st.header("📄 College documents")
    files = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True)
    if files and st.button("Index documents"):
        for f in files:
            pages = rag.extract_pdf(f.read())
            if not pages:
                st.warning(f"{f.name}: no extractable text (scanned? add OCR)"); continue
            text = "\n".join(t for _, t in pages)
            old = db.get_notice(f.name)
            if old is not None and old != text:
                st.session_state.setdefault("changes", {})[f.name] = rag.diff_text(old, text)
            db.save_notice(f.name, text)
            st.success(f"{f.name}: {rag.ingest(f.name, pages)} chunks indexed")
    st.metric("Indexed chunks", rag.count())
    profile = st.text_area("Your details (for eligibility)", placeholder="Dept: CSE, Sem 5, CGPA 8.2, family income 3L")

tab_ask, tab_tasks, tab_changes = st.tabs(["💬 Ask", "✅ My Tasks", "🔄 Notice Changes"])

# ---------- ask ----------
with tab_ask:
    q = st.text_input("Ask a question", placeholder="How do I apply for a bonafide certificate?")
    if st.button("Ask", type="primary") and q:
        if not os.getenv("ANTHROPIC_API_KEY"):
            st.error("Set ANTHROPIC_API_KEY first.")
        else:
            with st.spinner("Agents working..."):
                st.session_state["res"] = agents.run(q, profile)
    r = st.session_state.get("res")
    if r:
        st.subheader("Answer"); st.write(r["answer"])
        if r["eligibility"]:
            st.subheader("Eligibility check"); st.write(r["eligibility"])
        if r["plan"] and r["plan"].get("steps"):
            p = r["plan"]; st.subheader(f"Checklist: {p['procedure']}")
            if p.get("documents"):
                st.markdown("**Required documents**\n" + "\n".join(f"- {d}" for d in p["documents"]))
            for i, s in enumerate(p["steps"], 1):
                st.markdown(f"{i}. {s['step']}  \n   _{s.get('deadline') or 'no deadline stated'}_ · {s.get('source','')}")
            if st.button("➕ Save to My Tasks"):
                db.add_tasks(p["procedure"], p["steps"]); st.success("Saved")
        st.subheader("Verification"); st.info(r["verification"])
        with st.expander("🔍 Agent trace"):
            for t in r["trace"]:
                st.markdown(f"**{t['agent']}** → {t['detail']}")
        with st.expander("📚 Sources"):
            for c in r["chunks"]:
                st.markdown(f"**{c['source']} (p.{c['page']})**"); st.caption(c["text"])

# ---------- tasks ----------
with tab_tasks:
    tasks = db.all_tasks()
    if not tasks: st.info("No tasks yet. Ask a question and save the checklist.")
    today = datetime.date.today().isoformat()
    for t in tasks:
        overdue = t["deadline"] and t["deadline"][:10] < today and t["status"] != "done"
        c1, c2, c3 = st.columns([6, 2, 1])
        c1.markdown(f"{'⚠️ ' if overdue else ''}**{t['procedure']}**: {t['step']}  \n"
                    f"_{t['deadline'] or 'no deadline'}_ · {t['source']}")
        new = c2.selectbox("Status", ["pending", "done", "blocked"], key=f"s{t['id']}",
                           index=["pending", "done", "blocked"].index(t["status"]),
                           label_visibility="collapsed")
        if new != t["status"]: db.set_status(t["id"], new, t["note"] or ""); st.rerun()
        if c3.button("🗑", key=f"d{t['id']}"): db.delete_task(t["id"]); st.rerun()
        if new == "blocked" or overdue:
            why = st.text_input("What went wrong?", key=f"w{t['id']}")
            if why and st.button("Get recovery plan", key=f"r{t['id']}"):
                st.info(agents.recovery_agent(t, why, rag.search(t["step"], 4)))
    if tasks:
        done = sum(t["status"] == "done" for t in tasks)
        st.progress(done / len(tasks), text=f"{done}/{len(tasks)} complete")

# ---------- changes ----------
with tab_changes:
    ch = st.session_state.get("changes", {})
    if not ch: st.info("Re-upload an updated version of a notice (same filename) to see what changed.")
    for name, lines in ch.items():
        st.subheader(name)
        st.code("\n".join(lines[:80]) or "No line-level changes", language="diff")
