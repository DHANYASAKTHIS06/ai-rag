"""CampusCopilot — Login & Registration page"""
import streamlit as st
import db
import ui

def show():
    ui.inject_css()
    # Centered layout
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown("""
        <div style="text-align:center;padding:2rem 0 1.5rem">
          <div style="display:inline-flex;align-items:center;justify-content:center;
                      width:56px;height:56px;border-radius:14px;
                      background:linear-gradient(135deg,#2563EB,#4F46E5);
                      font-size:1.75rem;margin-bottom:1rem">🎓</div>
          <h1 style="font-size:1.6rem;font-weight:800;color:#0F172A;margin:0">CampusCopilot</h1>
          <p style="color:#475569;font-size:.9rem;margin:.35rem 0 0">
            AI-powered campus assistance platform
          </p>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_reg = st.tabs(["Sign In", "Create Account"])

        # ── Login ──
        with tab_login:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password",
                                         placeholder="Enter your password")
                submitted = st.form_submit_button("Sign In", type="primary",
                                                  use_container_width=True)
            if submitted:
                if not username or not password:
                    st.error("Please enter username and password.")
                else:
                    user = db.authenticate(username.strip(), password)
                    if user:
                        token = db.create_session(user["id"])
                        st.session_state["auth_token"] = token
                        st.session_state["user"] = user
                        st.session_state["current_page"] = "dashboard"
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password.")
            st.markdown("""
            <div style="text-align:center;margin-top:.75rem;font-size:.8rem;color:#94A3B8">
              Demo: admin / admin123 &nbsp;|&nbsp; officer / officer123
            </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Registration ──
        with tab_reg:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            with st.form("reg_form"):
                r_name     = st.text_input("Full Name *", placeholder="Your full name")
                r_user     = st.text_input("Username *", placeholder="Choose a username")
                r_email    = st.text_input("Email", placeholder="student@college.edu")
                r_dept     = st.text_input("Department", placeholder="e.g. Computer Science")
                r_sem      = st.text_input("Semester", placeholder="e.g. 5")
                r_cgpa     = st.text_input("CGPA", placeholder="e.g. 8.2")
                r_income   = st.text_input("Family Annual Income (₹)", placeholder="e.g. 300000")
                r_pass     = st.text_input("Password *", type="password")
                r_pass2    = st.text_input("Confirm Password *", type="password")
                reg_submit = st.form_submit_button("Create Account", type="primary",
                                                   use_container_width=True)
            if reg_submit:
                if not r_name or not r_user or not r_pass:
                    st.error("Full name, username, and password are required.")
                elif r_pass != r_pass2:
                    st.error("Passwords do not match.")
                elif len(r_pass) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    uid = db.create_user(
                        username=r_user.strip(), email=r_email.strip(),
                        password=r_pass, role="student",
                        full_name=r_name.strip(), department=r_dept,
                        semester=r_sem, cgpa=r_cgpa, family_income=r_income,
                    )
                    if uid:
                        st.success("✅ Account created! Please sign in.")
                    else:
                        st.error("Username or email already exists. Please choose another.")
            st.markdown('</div>', unsafe_allow_html=True)
