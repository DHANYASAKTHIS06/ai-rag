"""CampusCopilot — AI Chat page"""
import streamlit as st
import datetime
import agents, db, ui, rag

def show(user: dict):
    ui.inject_css()
    ui.render_sidebar(user)
    ui.page_header("💬 AI Chat", "Ask anything about campus procedures, scholarships, certificates, and more.")

    uid = user["id"]

    # ── Profile for eligibility context ───────────────────────────────────
    with st.sidebar:
        st.markdown("---")
        st.markdown("**Your Profile (for eligibility)**")
        profile_parts = []
        if user.get("department"):  profile_parts.append(f"Dept: {user['department']}")
        if user.get("semester"):    profile_parts.append(f"Sem: {user['semester']}")
        if user.get("cgpa"):        profile_parts.append(f"CGPA: {user['cgpa']}")
        if user.get("family_income"): profile_parts.append(f"Income: ₹{user['family_income']}")
        default_profile = ", ".join(profile_parts)
        profile = st.text_area("Profile details", value=default_profile,
                               placeholder="Dept: CSE, Sem 5, CGPA 8.2, Income: 300000",
                               help="Used by the Eligibility Agent.", height=90)

        # Language selector
        language_hint = st.selectbox("Response language",
                                     ["Auto-detect", "English", "Tamil", "Hindi", "Telugu"])

        # Clear chat
        if st.button("🗑 Clear Chat History", use_container_width=True):
            st.session_state["chat_messages"] = []
            db.delete_chat_history(uid)
            st.rerun()

    # ── Load chat history ──────────────────────────────────────────────────
    if "chat_messages" not in st.session_state:
        history = db.get_chat_history(uid, limit=20)
        st.session_state["chat_messages"] = []
        for h in history:
            st.session_state["chat_messages"].append({"role": "user", "content": h["question"]})
            st.session_state["chat_messages"].append({
                "role": "ai", "content": h["answer"],
                "chunks": h.get("sources", []),
                "verification": None, "eligibility": None, "plan": None,
            })

    messages = st.session_state["chat_messages"]

    # ── Render messages ────────────────────────────────────────────────────
    if not messages:
        st.markdown("""
        <div style="text-align:center;padding:3rem 1rem;color:#94A3B8">
          <div style="font-size:3rem;margin-bottom:1rem">🤖</div>
          <h3 style="color:#475569;font-weight:600">How can I help you today?</h3>
          <p style="font-size:.88rem">Ask me anything about college procedures, scholarships,
          eligibility, or certificates.</p>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for msg in messages:
            if msg["role"] == "user":
                ui.render_chat_message("user", msg["content"])
            else:
                ui.render_chat_message("ai", msg["content"])
                # Show extra panels below AI message
                if msg.get("eligibility"):
                    with st.expander("🎯 Eligibility Analysis"):
                        ui.render_eligibility(msg["eligibility"])
                if msg.get("plan") and msg["plan"].get("steps"):
                    with st.expander("📋 Application Checklist"):
                        ui.render_plan(msg["plan"], user_id=uid)
                if msg.get("chunks"):
                    ui.render_sources(msg["chunks"])
                if msg.get("verification"):
                    ui.render_verification(msg["verification"])
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Input area ─────────────────────────────────────────────────────────
    # Pre-fill from dashboard suggestion
    prefill = st.session_state.pop("prefill_question", "")

    st.markdown("---")
    with st.form("chat_form", clear_on_submit=True):
        q = st.text_input("Ask a question",
                           value=prefill,
                           placeholder="e.g. How do I apply for a bonafide certificate?",
                           label_visibility="collapsed")
        col_send, col_new = st.columns([3, 1])
        with col_send:
            submitted = st.form_submit_button("Send ➤", type="primary", use_container_width=True)
        with col_new:
            new_chat  = st.form_submit_button("New Chat 🔄", use_container_width=True)

    if new_chat:
        st.session_state["chat_messages"] = []
        st.rerun()

    if submitted and q.strip():
        # Check API key
        import os
        key = os.getenv("ANTHROPIC_API_KEY") or \
              (st.secrets.get("ANTHROPIC_API_KEY") if hasattr(st, "secrets") else None)
        if not key:
            st.error("⚠️ ANTHROPIC_API_KEY is not configured. Please contact the administrator.")
            st.stop()

        # Add user message
        messages.append({"role": "user", "content": q.strip()})

        # Apply language override
        lang_map = {"Tamil": "tamil", "Hindi": "hindi", "Telugu": "telugu",
                    "English": "english", "Auto-detect": None}
        lang_override = lang_map.get(language_hint)

        with st.spinner("🤖 Agents are working on your question..."):
            try:
                result = agents.run(q.strip(), profile=profile, user_id=uid)
                if lang_override:
                    result["language"] = lang_override
                answer = result["answer"]
            except Exception as e:
                result = {"answer": f"❌ Error: {e}", "chunks": [], "verification": None,
                          "eligibility": None, "plan": None, "language": "english", "intent": "general"}
                answer = result["answer"]

        # Save to DB
        db.save_chat(uid, q.strip(), answer,
                     sources=result.get("chunks", []),
                     language=result.get("language", "english"))

        # Append AI message
        messages.append({
            "role": "ai", "content": answer,
            "chunks": result.get("chunks", []),
            "verification": result.get("verification"),
            "eligibility": result.get("eligibility"),
            "plan": result.get("plan"),
        })
        st.session_state["chat_messages"] = messages
        st.rerun()
