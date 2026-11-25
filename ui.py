"""
CampusCopilot — UI utilities
Shared helper functions for styling, auth checks, navigation, and rendering.
"""
import os, re, datetime
import streamlit as st

# ─── CSS injection ───────────────────────────────────────────────────────────────
def inject_css():
    css_path = os.path.join(os.path.dirname(__file__), ".streamlit", "style.css")
    if os.path.exists(css_path):
        with open(css_path) as f:
            css = f.read()
    else:
        css = ""
    # Additional inline overrides
    extra = """
    <style>
    div[data-testid="stTabs"] button {
        font-size:.875rem!important; font-weight:500!important; color:#475569!important;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        color:#2563EB!important; font-weight:600!important;
    }
    .stSpinner>div { border-top-color:#2563EB!important; }
    div[data-testid="stMetricValue"] { font-size:1.6rem!important; font-weight:700!important; }
    </style>
    """
    st.markdown(f"<style>{css}</style>{extra}", unsafe_allow_html=True)

# ─── Auth helpers ────────────────────────────────────────────────────────────────
def get_current_user() -> dict | None:
    """Return the logged-in user dict or None."""
    token = st.session_state.get("auth_token")
    if not token:
        return None
    import db
    user = db.get_session(token)
    if user:
        st.session_state["user"] = user
    return user

def require_auth(role=None):
    """
    Redirect to login if not authenticated.
    If role is specified, also check that the user has that role.
    """
    user = get_current_user()
    if not user:
        st.session_state["redirect_after_login"] = st.session_state.get("current_page", "")
        st.session_state["current_page"] = "login"
        st.rerun()
    if role and isinstance(role, str) and user.get("role") != role:
        st.error("⛔ Access denied. You do not have permission to view this page.")
        st.stop()
    if role and isinstance(role, (list, tuple)) and user.get("role") not in role:
        st.error("⛔ Access denied. You do not have permission to view this page.")
        st.stop()
    return user

def logout():
    import db
    token = st.session_state.pop("auth_token", None)
    if token:
        db.delete_session(token)
    st.session_state.pop("user", None)
    st.session_state["current_page"] = "login"

# ─── Sidebar render ───────────────────────────────────────────────────────────────
def render_sidebar(user: dict):
    role = user.get("role", "student")
    name = user.get("full_name") or user.get("username", "")
    with st.sidebar:
        # Logo
        st.markdown("""
        <div class="sidebar-logo">
          <div class="sidebar-logo-icon">🎓</div>
          <div class="sidebar-logo-text">
            <h2>CampusCopilot</h2>
            <p>AI Campus Assistant</p>
          </div>
        </div>
        """, unsafe_allow_html=True)

        current = st.session_state.get("current_page", "dashboard")

        def nav(icon, label, page):
            is_active = current == page
            cls = "nav-item active" if is_active else "nav-item"
            if st.button(f"{icon}  {label}", key=f"nav_{page}",
                         use_container_width=True,
                         type="primary" if is_active else "secondary"):
                st.session_state["current_page"] = page
                st.rerun()

        # Student navigation
        if role == "student":
            st.markdown('<p class="nav-section-label">Main</p>', unsafe_allow_html=True)
            nav("🏠", "Dashboard",        "dashboard")
            nav("💬", "AI Chat",          "chat")
            nav("✅", "My Tasks",          "tasks")
            nav("🎯", "Eligibility Check", "eligibility")
            nav("📝", "Application Studio","application")
            st.markdown('<p class="nav-section-label">Support</p>', unsafe_allow_html=True)
            nav("🎫", "Helpdesk",         "helpdesk")
            nav("👤", "My Profile",       "profile")

        # Admin navigation
        elif role == "admin":
            st.markdown('<p class="nav-section-label">Administration</p>', unsafe_allow_html=True)
            nav("🏠", "Dashboard",        "dashboard")
            nav("📄", "Documents",        "documents")
            nav("👥", "Students",         "students")
            nav("🎫", "All Tickets",      "tickets")
            nav("⚙️", "Settings",         "settings")

        # Officer navigation
        elif role == "officer":
            st.markdown('<p class="nav-section-label">Helpdesk</p>', unsafe_allow_html=True)
            nav("🏠", "Dashboard",        "dashboard")
            nav("🎫", "Tickets",          "tickets")
            nav("👤", "My Profile",       "profile")

        # User card at bottom
        initials = "".join(w[0].upper() for w in name.split()[:2]) or name[:2].upper()
        role_label = {"student": "Student", "admin": "Administrator",
                      "officer": "Helpdesk Officer"}.get(role, role.title())
        st.markdown(f"""
        <div class="sidebar-user">
          <div class="sidebar-user-card">
            <div class="sidebar-avatar">{initials}</div>
            <div class="sidebar-user-info">
              <p class="sidebar-user-name">{name}</p>
              <p class="sidebar-user-role">{role_label}</p>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("")
        if st.button("🚪  Sign Out", use_container_width=True):
            logout()
            st.rerun()

# ─── Rendering helpers ────────────────────────────────────────────────────────────
def page_header(title: str, subtitle: str = ""):
    st.markdown(f"""
    <div class="page-header">
      <h1>{title}</h1>
      {"<p>" + subtitle + "</p>" if subtitle else ""}
    </div>
    """, unsafe_allow_html=True)

def card(content_html: str, padding: str = "1.5rem"):
    st.markdown(
        f'<div class="card" style="padding:{padding}">{content_html}</div>',
        unsafe_allow_html=True
    )

def badge(text: str, color: str = "blue") -> str:
    return f'<span class="badge badge-{color}">{text}</span>'

def status_badge(status: str) -> str:
    colors = {
        "open":        "blue",
        "in_progress": "yellow",
        "resolved":    "green",
        "closed":      "grey",
        "pending":     "yellow",
        "done":        "green",
        "blocked":     "red",
        "safe":        "green",
        "unsafe":      "red",
        "pending_scan":"yellow",
    }
    return badge(status.replace("_", " ").title(), colors.get(status, "grey"))

def render_chat_message(role: str, content: str, timestamp: str = ""):
    """Render a single chat bubble."""
    if role == "user":
        initials = st.session_state.get("user", {}).get("full_name", "U")
        initials = "".join(w[0].upper() for w in initials.split()[:2]) or "U"
        st.markdown(f"""
        <div class="chat-msg user">
          <div class="chat-avatar user-av">{initials}</div>
          <div>
            <div class="chat-bubble user">{content}</div>
            {"<div class='chat-time'>" + timestamp + "</div>" if timestamp else ""}
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Format citations [1],[2] in AI response
        formatted = re.sub(
            r'\[(\d+)\]',
            r'<span class="citation">[\1]</span>',
            content
        )
        # Convert markdown-style bold
        formatted = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', formatted)
        formatted = re.sub(r'\n', r'<br>', formatted)
        st.markdown(f"""
        <div class="chat-msg">
          <div class="chat-avatar ai-av">🤖</div>
          <div>
            <div class="chat-bubble ai">{formatted}</div>
            {"<div class='chat-time'>" + timestamp + "</div>" if timestamp else ""}
          </div>
        </div>
        """, unsafe_allow_html=True)

def render_eligibility(elig: dict):
    """Render structured eligibility result with three sections."""
    if not elig:
        return
    met      = elig.get("met", [])
    not_met  = elig.get("not_met", [])
    missing  = elig.get("missing", [])
    summary  = elig.get("summary", "")
    can_app  = elig.get("can_apply", False)

    if summary:
        color = "success" if can_app else "warning"
        icon  = "✅" if can_app else "⚠️"
        st.markdown(f"""
        <div class="cc-alert {color}" style="margin-bottom:1rem">
          <span style="font-size:1.1rem">{icon}</span>
          <span><strong>Assessment:</strong> {summary}</span>
        </div>
        """, unsafe_allow_html=True)

    if met:
        items = "".join(f'<div class="elig-item"><span style="color:#16A34A">✓</span> {m}</div>' for m in met)
        st.markdown(f"""
        <div class="elig-section elig-met">
          <div class="elig-header">✅ Criteria Met ({len(met)})</div>
          <div class="elig-body">{items}</div>
        </div>""", unsafe_allow_html=True)

    if not_met:
        items = "".join(f'<div class="elig-item"><span style="color:#DC2626">✗</span> {m}</div>' for m in not_met)
        st.markdown(f"""
        <div class="elig-section elig-notmet">
          <div class="elig-header">❌ Criteria Not Met ({len(not_met)})</div>
          <div class="elig-body">{items}</div>
        </div>""", unsafe_allow_html=True)

    if missing:
        items = "".join(f'<div class="elig-item"><span style="color:#D97706">?</span> {m}</div>' for m in missing)
        st.markdown(f"""
        <div class="elig-section elig-miss">
          <div class="elig-header">❓ Missing Information ({len(missing)})</div>
          <div class="elig-body">{items}</div>
        </div>""", unsafe_allow_html=True)

def render_sources(chunks: list[dict]):
    """Render collapsible source references."""
    if not chunks:
        return
    with st.expander(f"📚 Sources ({len(chunks)} references)"):
        for i, c in enumerate(chunks, 1):
            st.markdown(f"""
            <div class="card-sm" style="margin-bottom:.5rem">
              <div style="display:flex;justify-content:space-between;margin-bottom:.4rem">
                <span class="badge badge-blue">[{i}]</span>
                <span style="font-size:.78rem;color:#475569">
                  📄 {c['source']}  •  Page {c['page']}
                </span>
              </div>
              <p style="font-size:.82rem;color:#334155;margin:0;line-height:1.5">
                {c['text'][:300]}{"..." if len(c['text']) > 300 else ""}
              </p>
            </div>
            """, unsafe_allow_html=True)

def render_verification(ver: dict):
    """Render verification result."""
    if not ver:
        return
    verified = ver.get("verified", True)
    issues   = ver.get("issues", [])
    summary  = ver.get("summary", "")
    if verified:
        st.markdown(f"""
        <div class="cc-alert success">
          <span>✅</span>
          <span><strong>Verified:</strong> {summary}</span>
        </div>""", unsafe_allow_html=True)
    else:
        issue_html = "".join(f"<li>{i}</li>" for i in issues)
        st.markdown(f"""
        <div class="cc-alert warning">
          <span>⚠️</span>
          <div>
            <strong>Verification Notes:</strong> {summary}
            <ul style="margin:.5rem 0 0;padding-left:1.25rem;font-size:.84rem">
              {issue_html}
            </ul>
          </div>
        </div>""", unsafe_allow_html=True)

def render_plan(plan: dict, user_id=None):
    """Render planning checklist with save-to-tasks option."""
    if not plan or not plan.get("steps"):
        return
    import db
    st.markdown(f"""
    <div class="page-header" style="margin-bottom:1rem">
      <h2 style="font-size:1.1rem;font-weight:700;color:#0F172A">
        📋 Checklist: {plan.get('procedure', 'Application Steps')}
      </h2>
    </div>""", unsafe_allow_html=True)

    docs = plan.get("documents", [])
    if docs:
        st.markdown("**📁 Required Documents**")
        for d in docs:
            st.markdown(f"- {d}")

    today = datetime.date.today().isoformat()
    steps = plan.get("steps", [])
    for i, s in enumerate(steps, 1):
        dl = s.get("deadline") or ""
        overdue = dl and dl[:10] < today
        icon  = "⚠️" if overdue else f"{i}."
        color = "#DC2626" if overdue else "#0F172A"
        st.markdown(f"""
        <div class="checklist-item">
          <div style="font-size:.85rem;font-weight:600;color:{color};min-width:1.5rem">{icon}</div>
          <div style="flex:1">
            <div style="font-size:.88rem;font-weight:500;color:#0F172A">{s.get('step','')}</div>
            <div style="font-size:.78rem;color:#475569;margin-top:.2rem">
              {('📅 ' + dl) if dl else 'No deadline stated'}
              {(' · ' + s.get('source','')) if s.get('source') else ''}
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

    if user_id:
        st.markdown("")
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("💾 Save to My Tasks", type="primary", use_container_width=True):
                db.add_tasks(user_id, plan.get("procedure", ""), steps)
                st.success("✅ Tasks saved! View them in My Tasks.")

        # ICS calendar export
        with col2:
            ics_events = []
            for s in steps:
                dl = s.get("deadline")
                if dl:
                    try:
                        dt = datetime.date.fromisoformat(dl[:10])
                        dtstr = dt.strftime("%Y%m%d")
                        ics_events.append(
                            f"BEGIN:VEVENT\r\nSUMMARY:{s.get('step','Task')}\r\n"
                            f"DTSTART;VALUE=DATE:{dtstr}\r\nDTEND;VALUE=DATE:{dtstr}\r\n"
                            f"DESCRIPTION:{plan.get('procedure','')}\r\nEND:VEVENT"
                        )
                    except Exception:
                        pass
            if ics_events:
                ics = (
                    "BEGIN:VCALENDAR\r\nVERSION:2.0\r\n"
                    "PRODID:-//CampusCopilot//EN\r\n"
                    + "\r\n".join(ics_events)
                    + "\r\nEND:VCALENDAR"
                )
                st.download_button(
                    "📅 Export to Calendar (.ics)",
                    data=ics.encode(),
                    file_name="campuscopilot_tasks.ics",
                    mime="text/calendar",
                    use_container_width=True,
                )
