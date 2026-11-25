"""CampusCopilot — Eligibility Checker page"""
import streamlit as st
import agents, rag, db, ui

def show(user: dict):
    ui.inject_css()
    ui.render_sidebar(user)
    ui.page_header("🎯 Eligibility Checker",
                   "Check your eligibility for scholarships, certificates, and programs.")

    uid = user["id"]

    # ── Profile panel ─────────────────────────────────────────────────────
    with st.expander("📋 My Academic Profile", expanded=not bool(user.get("department"))):
        with st.form("profile_form"):
            c1, c2 = st.columns(2)
            with c1:
                f_name   = st.text_input("Full Name",    value=user.get("full_name",""))
                dept     = st.text_input("Department",   value=user.get("department",""),
                                         placeholder="e.g. Computer Science Engineering")
                sem      = st.text_input("Semester",     value=user.get("semester",""),
                                         placeholder="e.g. 5")
            with c2:
                cgpa     = st.text_input("CGPA",         value=user.get("cgpa",""),
                                         placeholder="e.g. 8.2")
                income   = st.text_input("Family Annual Income (₹)", value=user.get("family_income",""),
                                         placeholder="e.g. 300000")
                extra    = st.text_area("Additional details",
                                        placeholder="Scholarship category, caste certificate, etc.",
                                        height=80)
            save_p = st.form_submit_button("Save Profile", type="primary")
        if save_p:
            db.update_user_profile(uid, f_name, dept, sem, cgpa, income)
            st.success("✅ Profile saved!")
            st.rerun()

    # Build profile string for agents
    profile_parts = []
    if user.get("full_name"):     profile_parts.append(user["full_name"])
    if user.get("department"):    profile_parts.append(f"Dept: {user['department']}")
    if user.get("semester"):      profile_parts.append(f"Sem: {user['semester']}")
    if user.get("cgpa"):          profile_parts.append(f"CGPA: {user['cgpa']}")
    if user.get("family_income"): profile_parts.append(f"Income: ₹{user['family_income']}")
    profile_str = ", ".join(profile_parts)

    st.markdown("---")

    # ── Eligibility query ─────────────────────────────────────────────────
    st.markdown("### 🔍 Check Eligibility")
    quick_checks = [
        "Am I eligible for the merit scholarship?",
        "Can I apply for fee waiver?",
        "Am I eligible for the need-based scholarship?",
        "What scholarships can I apply for?",
        "Am I eligible for hostel accommodation?",
    ]
    selected_q = st.selectbox("Quick check", ["-- Select a quick check --"] + quick_checks)

    with st.form("elig_form"):
        q = st.text_area(
            "What do you want to check eligibility for?",
            value=selected_q if selected_q != "-- Select a quick check --" else "",
            placeholder="e.g. Am I eligible for the merit scholarship?",
            height=90,
        )
        check_btn = st.form_submit_button("Check Eligibility ✓", type="primary",
                                          use_container_width=True)

    if check_btn and q.strip():
        import os
        key = os.getenv("ANTHROPIC_API_KEY") or \
              (st.secrets.get("ANTHROPIC_API_KEY") if hasattr(st, "secrets") else None)
        if not key:
            st.error("⚠️ AI is not configured. Contact administrator.")
            st.stop()

        with st.spinner("🤖 Evaluating your eligibility..."):
            chunks = rag.search(q, 6)
            if not chunks:
                st.warning("⚠️ No documents indexed yet. Ask an admin to upload college policy PDFs.")
            else:
                elig = agents.eligibility_agent(q, chunks, profile_str)
                answer = agents.knowledge_agent(q, chunks)

                st.markdown("### 📊 Eligibility Results")
                ui.render_eligibility(elig)

                with st.expander("📝 Detailed Answer"):
                    st.markdown(answer)

                ui.render_sources(chunks)

                # Save to chat history
                db.save_chat(uid, q, answer, sources=chunks)
