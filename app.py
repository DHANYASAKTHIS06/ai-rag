"""
CampusCopilot — Main Application Entry Point
Multi-role, multi-page Streamlit application.
Routes: login → student/admin/officer dashboards.
"""
# SQLite compatibility shim for Streamlit Cloud (must be first)
try:
    __import__("pysqlite3")
    import sys
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except Exception:
    pass

import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Inject secrets into env (Streamlit Cloud) ───────────────────────────────
try:
    if hasattr(st, "secrets"):
        for key in ["ANTHROPIC_API_KEY", "CLAUDE_MODEL", "DATABASE_PATH",
                    "CHROMA_PERSIST_DIRECTORY", "DOCUMENT_STORAGE_PATH",
                    "ADMIN_PASSWORD", "OFFICER_PASSWORD"]:
            if key in st.secrets and not os.getenv(key):
                os.environ[key] = st.secrets[key]
except Exception:
    pass

import db

# ── Page config (must be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="CampusCopilot",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "CampusCopilot — AI-powered campus assistant."},
)

# ── Database init ─────────────────────────────────────────────────────────────
db.init()

# ── Session state defaults ────────────────────────────────────────────────────
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "login"
if "auth_token" not in st.session_state:
    st.session_state["auth_token"] = None

# ── Auth helper ───────────────────────────────────────────────────────────────
def get_user():
    token = st.session_state.get("auth_token")
    if not token:
        return None
    return db.get_session(token)

# ── Route to page ─────────────────────────────────────────────────────────────
user = get_user()
page = st.session_state.get("current_page", "login")

# If not logged in → always show login
if not user:
    st.session_state["current_page"] = "login"
    import pages_login
    pages_login.show()
    st.stop()

# ── Logged in: role-based routing ─────────────────────────────────────────────
role = user.get("role", "student")

# Keep fresh user data
st.session_state["user"] = user

# ── STUDENT ROUTES ─────────────────────────────────────────────────────────────
if role == "student":
    if page in ("login", "dashboard"):
        import pages_student
        pages_student.show(user)
    elif page == "chat":
        import pages_chat
        pages_chat.show(user)
    elif page == "tasks":
        import pages_tasks
        pages_tasks.show(user)
    elif page == "eligibility":
        import pages_eligibility
        pages_eligibility.show(user)
    elif page == "application":
        import pages_application
        pages_application.show(user)
    elif page == "helpdesk":
        import pages_helpdesk_student
        pages_helpdesk_student.show(user)
    elif page == "profile":
        import pages_profile
        pages_profile.show(user)
    else:
        import pages_student
        pages_student.show(user)

# ── ADMIN ROUTES ───────────────────────────────────────────────────────────────
elif role == "admin":
    if page in ("login", "dashboard", "documents", "upload",
                "students", "tickets", "settings"):
        import pages_admin
        pages_admin.show(user)
    else:
        import pages_admin
        pages_admin.show(user)

# ── OFFICER ROUTES ─────────────────────────────────────────────────────────────
elif role == "officer":
    if page in ("login", "dashboard", "tickets"):
        import pages_officer
        pages_officer.show(user)
    elif page == "profile":
        import pages_profile
        pages_profile.show(user)
    else:
        import pages_officer
        pages_officer.show(user)

else:
    st.error("Unknown role. Please contact the administrator.")
    if st.button("Sign Out"):
        import ui
        ui.logout()
        st.rerun()
