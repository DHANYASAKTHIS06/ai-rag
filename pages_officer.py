"""CampusCopilot — Helpdesk Officer Dashboard"""
import streamlit as st
import db, rag, agents, ui

def show(user: dict):
    ui.inject_css()
    ui.render_sidebar(user)
    ui.page_header("🎫 Helpdesk Officer Dashboard",
                   "Manage student support tickets and generate AI-assisted responses.")

    officer_id = user["id"]
    all_tickets = db.get_tickets()

    # ── Stats ─────────────────────────────────────────────────────────────
    total  = len(all_tickets)
    open_t = sum(1 for t in all_tickets if t["status"] == "open")
    inprog = sum(1 for t in all_tickets if t["status"] == "in_progress")
    res_t  = sum(1 for t in all_tickets if t["status"] == "resolved")

    c1, c2, c3, c4 = st.columns(4)
    for col, (label, val, color) in zip([c1,c2,c3,c4], [
        ("Total Tickets", total,  "#0F172A"),
        ("Open",          open_t, "#2563EB"),
        ("In Progress",   inprog, "#D97706"),
        ("Resolved",      res_t,  "#16A34A"),
    ]):
        with col:
            st.markdown(f"""
            <div class="stat-card">
              <div class="stat-label">{label}</div>
              <div class="stat-value" style="color:{color}">{val}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Ticket list + detail ───────────────────────────────────────────────
    if not all_tickets:
        st.markdown("""
        <div class="cc-alert info">
          <span>ℹ️</span><span>No tickets submitted yet.</span>
        </div>""", unsafe_allow_html=True)
        return

    # Filter
    status_filter = st.selectbox(
        "Filter", ["All", "Open", "In Progress", "Resolved", "Closed"],
        label_visibility="visible"
    )
    filtered = all_tickets
    if status_filter != "All":
        filtered = [t for t in all_tickets
                    if t["status"].replace("_"," ").title() == status_filter]

    left, right = st.columns([1, 1.6])

    # ── Ticket list panel ─────────────────────────────────────────────────
    with left:
        st.markdown("### 📋 Tickets")
        selected_tid = st.session_state.get("selected_ticket_id")
        for t in filtered:
            badge_html = ui.status_badge(t["status"])
            is_sel = t["id"] == selected_tid
            border = "border-color:#2563EB" if is_sel else ""
            if st.button(
                f"#{t['id']} — {t['subject'][:35]}",
                key=f"sel_{t['id']}", use_container_width=True,
                type="primary" if is_sel else "secondary"
            ):
                st.session_state["selected_ticket_id"] = t["id"]
                st.rerun()

    # ── Ticket detail panel ───────────────────────────────────────────────
    with right:
        if not selected_tid:
            st.markdown("""
            <div class="cc-alert info" style="margin-top:2rem">
              <span>👈</span><span>Select a ticket from the list to view details.</span>
            </div>""", unsafe_allow_html=True)
        else:
            ticket = db.get_ticket(selected_tid)
            if not ticket:
                st.error("Ticket not found.")
            else:
                badge_html = ui.status_badge(ticket["status"])
                st.markdown(f"""
                <div class="card" style="padding:1.25rem">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                      <div style="font-size:1rem;font-weight:700;color:#0F172A">
                        #{ticket['id']} — {ticket['subject']}
                      </div>
                      <div style="font-size:.8rem;color:#64748B;margin-top:.25rem">
                        From: <strong>{ticket.get('student_name') or ticket.get('student_username','?')}</strong>
                        · {ticket.get('department','?')} Sem {ticket.get('semester','?')}
                        · {ticket.get('student_email','?')}
                      </div>
                      <div style="font-size:.78rem;color:#94A3B8">
                        Submitted: {ticket['created_at'][:10]}
                      </div>
                    </div>
                    {badge_html}
                  </div>
                </div>""", unsafe_allow_html=True)

                # Ticket description
                st.markdown('<div class="card" style="background:#F8FAFC;padding:1rem">'
                            '<strong style="font-size:.82rem;color:#475569">STUDENT\'S REQUEST</strong><br>',
                            unsafe_allow_html=True)
                st.markdown(ticket.get("description", ""))
                st.markdown('</div>', unsafe_allow_html=True)

                # AI-suggested response
                ai_col, _ = st.columns([2, 1])
                with ai_col:
                    if st.button("🤖 Generate AI Suggested Response",
                                 type="primary", use_container_width=True):
                        with st.spinner("🤖 Generating response..."):
                            chunks = rag.search(
                                ticket["subject"] + " " + ticket.get("description", ""), 5
                            )
                            suggestion = agents.helpdesk_agent(
                                ticket["subject"],
                                ticket.get("description", ""),
                                chunks
                            )
                        db.update_ticket(selected_tid, ai_suggestion=suggestion,
                                         status="in_progress",
                                         assigned_officer=officer_id)
                        st.session_state[f"edit_resp_{selected_tid}"] = suggestion
                        st.rerun()

                # Show AI suggestion
                ai_sugg = ticket.get("ai_suggestion", "")
                if ai_sugg:
                    st.markdown("""
                    <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;
                                padding:.875rem 1rem;margin:.75rem 0">
                      <div style="font-size:.78rem;font-weight:700;color:#1D4ED8;margin-bottom:.5rem">
                        🤖 AI SUGGESTED RESPONSE (review before sending)
                      </div>
                    """, unsafe_allow_html=True)
                    st.markdown(ai_sugg)
                    st.markdown("</div>", unsafe_allow_html=True)

                # Officer editable response
                current_resp = st.session_state.get(
                    f"edit_resp_{selected_tid}",
                    ticket.get("officer_response") or ai_sugg or ""
                )
                officer_response = st.text_area(
                    "✏️ Your Response (edit before sending):",
                    value=current_resp,
                    height=200,
                    key=f"officer_resp_{selected_tid}"
                )
                st.session_state[f"edit_resp_{selected_tid}"] = officer_response

                # Status + Send
                new_status = st.selectbox(
                    "Update Status",
                    ["open", "in_progress", "resolved", "closed"],
                    index=["open","in_progress","resolved","closed"].index(ticket["status"]),
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Send Response & Update Status",
                                 type="primary", use_container_width=True):
                        if not officer_response.strip():
                            st.error("Please write a response before sending.")
                        else:
                            db.update_ticket(
                                selected_tid,
                                status=new_status,
                                officer_response=officer_response,
                                assigned_officer=officer_id,
                            )
                            st.success("✅ Response sent to student!")
                            st.rerun()
                with col2:
                    if st.button("💾 Save Draft", use_container_width=True):
                        db.update_ticket(selected_tid, status=new_status,
                                         assigned_officer=officer_id)
                        st.info("Draft saved.")
                        st.rerun()

                # Show sources used
                if ai_sugg:
                    with st.expander("📚 Knowledge Base Sources Used"):
                        chunks = rag.search(
                            ticket["subject"] + " " + ticket.get("description",""), 4
                        )
                        ui.render_sources(chunks)
