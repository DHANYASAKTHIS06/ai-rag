"""CampusCopilot — Profile page (student & officer)"""
import streamlit as st
import db, ui

def show(user: dict):
    ui.inject_css()
    ui.render_sidebar(user)
    ui.page_header("👤 My Profile", "Manage your account information and preferences.")

    uid  = user["id"]
    role = user.get("role","student")

    tab_info, tab_pw = st.tabs(["📋 Profile Information", "🔒 Change Password"])

    with tab_info:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        with st.form("profile_form"):
            full_name = st.text_input("Full Name",    value=user.get("full_name",""))
            email     = st.text_input("Email",        value=user.get("email",""),
                                      disabled=True, help="Email cannot be changed")
            username  = st.text_input("Username",     value=user.get("username",""),
                                      disabled=True, help="Username cannot be changed")
            if role == "student":
                c1, c2 = st.columns(2)
                with c1:
                    dept   = st.text_input("Department",   value=user.get("department",""))
                    sem    = st.text_input("Semester",      value=user.get("semester",""))
                with c2:
                    cgpa   = st.text_input("CGPA",          value=user.get("cgpa",""))
                    income = st.text_input("Family Annual Income (₹)",
                                           value=user.get("family_income",""))
            else:
                dept = sem = cgpa = income = ""

            save = st.form_submit_button("Save Changes", type="primary")

        if save:
            db.update_user_profile(uid, full_name, dept, sem, cgpa, income)
            st.success("✅ Profile updated!")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab_pw:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        with st.form("pw_form"):
            old_pw  = st.text_input("Current Password", type="password")
            new_pw  = st.text_input("New Password",     type="password")
            conf_pw = st.text_input("Confirm Password", type="password")
            change  = st.form_submit_button("Change Password", type="primary")
        if change:
            current = db.get_user_by_id(uid)
            if not db.verify_password(old_pw, current["password_hash"]):
                st.error("❌ Current password is incorrect.")
            elif new_pw != conf_pw:
                st.error("❌ New passwords do not match.")
            elif len(new_pw) < 6:
                st.error("❌ Password must be at least 6 characters.")
            else:
                db.change_password(uid, new_pw)
                st.success("✅ Password changed successfully!")
        st.markdown('</div>', unsafe_allow_html=True)
