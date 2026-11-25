"""CampusCopilot — Student Dashboard page"""
import streamlit as st
import datetime
import db
import ui

def show(user: dict):
    ui.inject_css()
    ui.render_sidebar(user)
    ui.page_header(
        f"Welcome back, {user.get('full_name') or user.get('username')} 👋",
        "Here's what's happening with your campus activities."
    )

    uid = user["id"]
    # ── Stats row ──────────────────────────────────────────────────────────
    tasks   = db.all_tasks(uid)
    tickets = db.get_tickets(user_id=uid)
    done    = sum(1 for t in tasks if t["status"] == "done")
    pending = sum(1 for t in tasks if t["status"] == "pending")
    blocked = sum(1 for t in tasks if t["status"] == "blocked")
    today   = datetime.date.today().isoformat()
    overdue = sum(1 for t in tasks if t.get("deadline") and t["deadline"][:10] < today and t["status"] != "done")
    open_tk = sum(1 for t in tickets if t["status"] == "open")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="stat-card">
          <div class="stat-label">Total Tasks</div>
          <div class="stat-value">{len(tasks)}</div>
          <div class="stat-delta">{done} completed</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="stat-card">
          <div class="stat-label">Pending Tasks</div>
          <div class="stat-value" style="color:{'#D97706' if pending else '#0F172A'}">{pending}</div>
          <div class="stat-delta" style="color:{'#DC2626' if overdue else '#94A3B8'}">
            {f'⚠️ {overdue} overdue' if overdue else 'All on track'}
          </div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="stat-card">
          <div class="stat-label">Support Tickets</div>
          <div class="stat-value">{len(tickets)}</div>
          <div class="stat-delta">{open_tk} open</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        pct = int(done / len(tasks) * 100) if tasks else 0
        st.markdown(f"""
        <div class="stat-card">
          <div class="stat-label">Progress</div>
          <div class="stat-value">{pct}%</div>
          <div class="cc-progress-wrap" style="margin-top:.5rem">
            <div class="cc-progress-bar" style="width:{pct}%"></div>
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    left, right = st.columns([1.5, 1])

    # ── Recent tasks ───────────────────────────────────────────────────────
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📋 Recent Tasks")
        recent_tasks = sorted(tasks, key=lambda x: x.get("deadline") or "9999", )[:6]
        if not recent_tasks:
            st.markdown("""
            <div class="cc-alert info">
              <span>💡</span>
              <span>No tasks yet. Use <strong>AI Chat</strong> to ask about an application
              procedure and save the generated checklist.</span>
            </div>""", unsafe_allow_html=True)
        else:
            for t in recent_tasks:
                dl = t.get("deadline", "")
                is_overdue = dl and dl[:10] < today and t["status"] != "done"
                badge_html = ui.status_badge(t["status"])
                st.markdown(f"""
                <div class="checklist-item {'done' if t['status']=='done' else ''}">
                  <div style="flex:1">
                    <div style="font-size:.86rem;font-weight:500;color:#0F172A">
                      {'⚠️ ' if is_overdue else ''}{t['step']}
                    </div>
                    <div style="font-size:.76rem;color:#64748B;margin-top:.2rem">
                      {t['procedure']} · {dl or 'No deadline'}
                    </div>
                  </div>
                  {badge_html}
                </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Quick actions + recent tickets ────────────────────────────────────
    with right:
        # Quick actions
        st.markdown('<div class="card" style="margin-bottom:1rem">', unsafe_allow_html=True)
        st.markdown("### ⚡ Quick Actions")
        if st.button("💬  Ask AI Assistant", use_container_width=True, type="primary"):
            st.session_state["current_page"] = "chat"
            st.rerun()
        if st.button("🎯  Check Eligibility", use_container_width=True):
            st.session_state["current_page"] = "eligibility"
            st.rerun()
        if st.button("📝  Write Application Letter", use_container_width=True):
            st.session_state["current_page"] = "application"
            st.rerun()
        if st.button("🎫  Raise Support Ticket", use_container_width=True):
            st.session_state["current_page"] = "helpdesk"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # Recent tickets
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🎫 Recent Tickets")
        if not tickets:
            st.markdown('<p style="color:#94A3B8;font-size:.85rem">No tickets raised yet.</p>',
                        unsafe_allow_html=True)
        else:
            for t in tickets[:3]:
                badge_html = ui.status_badge(t["status"])
                resp = "✅ Response received" if t.get("officer_response") else "⏳ Awaiting response"
                st.markdown(f"""
                <div style="border-bottom:1px solid #F1F5F9;padding:.6rem 0">
                  <div style="display:flex;justify-content:space-between;align-items:center">
                    <span style="font-size:.84rem;font-weight:500;color:#0F172A">
                      {t['subject'][:40]}
                    </span>
                    {badge_html}
                  </div>
                  <div style="font-size:.75rem;color:#64748B;margin-top:.2rem">{resp}</div>
                </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Suggested questions ───────────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 💡 Suggested Questions")
    suggestions = [
        "How do I apply for a bonafide certificate?",
        "What are the scholarship eligibility criteria?",
        "How do I apply for fee exemption?",
        "What documents are needed for hostel admission?",
        "How do I get a transcript?",
        "What is the process for exam re-evaluation?",
    ]
    cols = st.columns(3)
    for i, q in enumerate(suggestions):
        with cols[i % 3]:
            if st.button(f"💬 {q}", use_container_width=True, key=f"sugg_{i}"):
                st.session_state["prefill_question"] = q
                st.session_state["current_page"] = "chat"
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
