"""CampusCopilot — Helpdesk page (student view)"""
import streamlit as st
import db, ui

def show(user: dict):
    ui.inject_css()
    ui.render_sidebar(user)
    ui.page_header("🎫 Helpdesk", "Raise a support ticket or view your previous requests.")

    uid = user["id"]

    tab_new, tab_my = st.tabs(["➕ New Ticket", "📋 My Tickets"])

    # ── New Ticket ────────────────────────────────────────────────────────
    with tab_new:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### Submit a Support Request")
        st.markdown('<p style="color:#475569;font-size:.88rem">Our helpdesk team will respond within 1-2 working days.</p>',
                    unsafe_allow_html=True)

        common_subjects = [
            "-- Select a common issue --",
            "Certificate Request",
            "Scholarship Enquiry",
            "Fee Concession Request",
            "Exam Related Issue",
            "Hostel Accommodation",
            "Library Issue",
            "Transport / Bus Pass",
            "Other",
        ]
        with st.form("ticket_form"):
            cat     = st.selectbox("Common Issues", common_subjects)
            subject = st.text_input("Subject *",
                                    value="" if cat == common_subjects[0] else cat,
                                    placeholder="Brief description of your issue")
            desc    = st.text_area("Description *",
                                   placeholder="Provide as much detail as possible...",
                                   height=160)
            submit_t = st.form_submit_button("Submit Ticket 🚀", type="primary",
                                             use_container_width=True)

        if submit_t:
            if not subject.strip() or not desc.strip():
                st.error("Please fill in both subject and description.")
            else:
                tid = db.create_ticket(uid, subject.strip(), desc.strip())
                st.success(f"✅ Ticket #{tid} submitted successfully! We'll respond soon.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── My Tickets ────────────────────────────────────────────────────────
    with tab_my:
        tickets = db.get_tickets(user_id=uid)
        if not tickets:
            st.markdown("""
            <div class="cc-alert info">
              <span>ℹ️</span><span>You haven't raised any tickets yet.</span>
            </div>""", unsafe_allow_html=True)
        else:
            for t in tickets:
                badge_html = ui.status_badge(t["status"])
                has_resp   = bool(t.get("officer_response"))
                st.markdown(f"""
                <div class="ticket-card">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                      <div style="font-size:.92rem;font-weight:600;color:#0F172A">
                        #{t['id']} — {t['subject']}
                      </div>
                      <div style="font-size:.78rem;color:#64748B;margin-top:.25rem">
                        Submitted: {t['created_at'][:10]}
                        {' · Updated: ' + t['updated_at'][:10] if t['updated_at'] != t['created_at'] else ''}
                      </div>
                    </div>
                    {badge_html}
                  </div>
                  <div style="font-size:.85rem;color:#334155;margin:.6rem 0;line-height:1.5">
                    {t['description'][:200]}{'...' if len(t.get('description','')) > 200 else ''}
                  </div>
                </div>
                """, unsafe_allow_html=True)

                if has_resp:
                    with st.expander(f"✅ View Response — Ticket #{t['id']}"):
                        st.markdown(f"""
                        <div class="cc-alert success">
                          <span>🧑‍💼</span>
                          <div>
                            <strong>Helpdesk Response:</strong><br>
                            <span style="font-size:.88rem">{t['officer_response']}</span>
                          </div>
                        </div>""", unsafe_allow_html=True)
