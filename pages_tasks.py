"""CampusCopilot — My Tasks page"""
import streamlit as st
import datetime
import db, ui, rag, agents

def show(user: dict):
    ui.inject_css()
    ui.render_sidebar(user)
    ui.page_header("✅ My Tasks", "Track your application steps, deadlines, and progress.")

    uid   = user["id"]
    tasks = db.all_tasks(uid)
    today = datetime.date.today().isoformat()

    if not tasks:
        st.markdown("""
        <div class="cc-alert info" style="margin-top:1rem">
          <span>💡</span>
          <span>No tasks yet. Use <strong>AI Chat</strong> to ask about an application procedure
          and save the generated checklist here.</span>
        </div>""", unsafe_allow_html=True)
        if st.button("💬 Go to AI Chat", type="primary"):
            st.session_state["current_page"] = "chat"
            st.rerun()
        return

    # ── Progress summary ──────────────────────────────────────────────────
    done    = sum(1 for t in tasks if t["status"] == "done")
    blocked = sum(1 for t in tasks if t["status"] == "blocked")
    pending = len(tasks) - done - blocked
    pct     = int(done / len(tasks) * 100)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-card"><div class="stat-label">Total</div>'
                    f'<div class="stat-value">{len(tasks)}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card"><div class="stat-label">Completed</div>'
                    f'<div class="stat-value" style="color:#16A34A">{done}</div></div>',
                    unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card"><div class="stat-label">Pending</div>'
                    f'<div class="stat-value" style="color:#D97706">{pending}</div></div>',
                    unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card"><div class="stat-label">Blocked</div>'
                    f'<div class="stat-value" style="color:#DC2626">{blocked}</div></div>',
                    unsafe_allow_html=True)

    st.markdown(f"""
    <div style="margin:1.25rem 0 .5rem">
      <div style="display:flex;justify-content:space-between;font-size:.82rem;color:#475569;margin-bottom:.35rem">
        <span>Overall Progress</span><span>{done}/{len(tasks)} tasks complete</span>
      </div>
      <div class="cc-progress-wrap">
        <div class="cc-progress-bar" style="width:{pct}%"></div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Filter ────────────────────────────────────────────────────────────
    filter_status = st.selectbox("Filter by status",
                                 ["All", "Pending", "Done", "Blocked"],
                                 label_visibility="visible")

    # ── Group by procedure ────────────────────────────────────────────────
    procedures = {}
    for t in tasks:
        proc = t.get("procedure", "General")
        procedures.setdefault(proc, []).append(t)

    for proc, proc_tasks in procedures.items():
        # Apply filter
        if filter_status != "All":
            proc_tasks = [t for t in proc_tasks if t["status"].lower() == filter_status.lower()]
        if not proc_tasks:
            continue

        done_p = sum(1 for t in proc_tasks if t["status"] == "done")
        st.markdown(f"""
        <div class="card" style="margin-bottom:.75rem;padding:1.1rem 1.25rem">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.75rem">
            <h3 style="font-size:.95rem;font-weight:700;color:#0F172A;margin:0">{proc}</h3>
            <span style="font-size:.78rem;color:#64748B">{done_p}/{len(proc_tasks)} done</span>
          </div>
        """, unsafe_allow_html=True)

        for t in proc_tasks:
            dl = t.get("deadline", "")
            overdue = dl and dl[:10] < today and t["status"] != "done"
            tid = t["id"]

            check_icon = {"done": "✅", "blocked": "🚫", "pending": "⬜"}.get(t["status"], "⬜")
            col1, col2, col3 = st.columns([6, 2, 1])
            with col1:
                st.markdown(f"""
                <div style="font-size:.86rem;font-weight:500;color:{'#DC2626' if overdue else '#0F172A'}">
                  {check_icon} {'⚠️ ' if overdue else ''}{t['step']}
                </div>
                <div style="font-size:.76rem;color:#64748B;margin-left:1.6rem">
                  {('📅 ' + dl) if dl else 'No deadline'} · {t.get('source','') or ''}
                </div>""", unsafe_allow_html=True)
            with col2:
                new_status = st.selectbox(
                    "Status", ["pending", "done", "blocked"],
                    index=["pending", "done", "blocked"].index(t["status"]),
                    key=f"st_{tid}", label_visibility="collapsed"
                )
                if new_status != t["status"]:
                    db.set_status(tid, new_status)
                    st.rerun()
            with col3:
                if st.button("🗑", key=f"del_{tid}", help="Delete task"):
                    db.delete_task(tid)
                    st.rerun()

            # Blocked: show recovery agent
            if t["status"] == "blocked" or overdue:
                with st.expander(f"🆘 Get Recovery Plan for this step"):
                    why = st.text_input("What went wrong?", key=f"why_{tid}",
                                        placeholder="Describe the issue...")
                    if why and st.button("Get Recovery Plan", key=f"rec_{tid}", type="primary"):
                        with st.spinner("Finding alternatives..."):
                            chunks = rag.search(t["step"], 4)
                            rec    = agents.recovery_agent(t, why, chunks)
                        st.markdown(f"""
                        <div class="cc-alert info">
                          <span>🔄</span><div>{rec}</div>
                        </div>""", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
