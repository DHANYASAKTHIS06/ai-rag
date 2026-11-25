"""CampusCopilot — Application Studio page"""
import streamlit as st
import datetime, io
import agents, db, ui

def show(user: dict):
    ui.inject_css()
    ui.render_sidebar(user)
    ui.page_header("📝 Application Studio",
                   "Generate professional application letters with AI assistance.")

    uid = user["id"]

    # ── Form ──────────────────────────────────────────────────────────────
    with st.form("app_letter_form"):
        st.markdown("### Letter Details")
        c1, c2 = st.columns(2)
        with c1:
            letter_types = [
                "Bonafide Certificate Request",
                "Fee Concession Request",
                "Scholarship Application",
                "Hostel Admission Request",
                "Transcript Request",
                "Character Certificate Request",
                "No Objection Certificate (NOC)",
                "Exam Re-evaluation Request",
                "Library No-Due Certificate",
                "Medical Leave Application",
                "Custom Letter",
            ]
            letter_type = st.selectbox("Letter Type *", letter_types)
            to_name     = st.text_input("To (Name & Title)",
                                        placeholder="The Principal / HOD / Dean")
            to_dept     = st.text_input("Department / Office",
                                        placeholder="Department of Computer Science")
            subject     = st.text_input("Subject *",
                                        placeholder="Request for Bonafide Certificate")
        with c2:
            s_name   = st.text_input("Your Full Name",
                                     value=user.get("full_name", ""))
            s_dept   = st.text_input("Your Department",
                                     value=user.get("department", ""))
            s_sem    = st.text_input("Semester / Year",
                                     value=user.get("semester", ""))
            s_rollno = st.text_input("Roll Number / Reg. No.",
                                     placeholder="e.g. 20CS001")

        details = st.text_area(
            "Additional details / body content",
            placeholder="Explain your purpose, any specific requirements, relevant dates, etc.",
            height=120,
        )
        gen_btn = st.form_submit_button("✨ Generate Letter with AI", type="primary",
                                        use_container_width=True)

    if gen_btn:
        if not letter_type or not subject.strip():
            st.error("Please fill in letter type and subject.")
            return

        import os
        key = os.getenv("ANTHROPIC_API_KEY") or \
              (st.secrets.get("ANTHROPIC_API_KEY") if hasattr(st, "secrets") else None)
        if not key:
            st.error("⚠️ AI not configured. Contact administrator.")
            return

        student_info = {
            "name": s_name, "department": s_dept,
            "semester": s_sem, "roll_number": s_rollno,
            "date": datetime.date.today().strftime("%d %B %Y"),
        }
        recipient_info = {
            "name": to_name, "department": to_dept,
            "institution": "College of Engineering",
        }

        with st.spinner("✨ Drafting your letter..."):
            letter_text = agents.application_letter_agent(
                letter_type, student_info, recipient_info, subject, details
            )

        st.session_state["generated_letter"] = letter_text
        st.session_state["letter_subject"]   = subject
        st.rerun()

    # ── Show generated letter ──────────────────────────────────────────────
    if "generated_letter" in st.session_state:
        letter = st.session_state["generated_letter"]
        subject_txt = st.session_state.get("letter_subject", "Application")

        st.markdown("### 📄 Generated Letter")
        st.markdown('<div class="card">', unsafe_allow_html=True)

        # Editable preview
        edited_letter = st.text_area("Review and edit your letter:",
                                     value=letter, height=400)

        c1, c2, c3 = st.columns(3)
        with c1:
            # Plain text download
            st.download_button(
                "⬇️ Download as .txt",
                data=edited_letter.encode("utf-8"),
                file_name=f"application_{subject_txt[:30].replace(' ','_')}.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with c2:
            # PDF download
            pdf_bytes = _make_pdf(edited_letter, subject_txt)
            if pdf_bytes:
                st.download_button(
                    "📄 Download as PDF",
                    data=pdf_bytes,
                    file_name=f"application_{subject_txt[:30].replace(' ','_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        with c3:
            if st.button("🔄 Regenerate", use_container_width=True):
                del st.session_state["generated_letter"]
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


def _make_pdf(text: str, title: str) -> bytes | None:
    """Generate a simple A4 PDF from letter text using reportlab if available."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles    import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units     import cm
        from reportlab.platypus      import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib           import colors

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                leftMargin=3*cm, rightMargin=3*cm,
                                topMargin=3*cm, bottomMargin=3*cm)
        styles = getSampleStyleSheet()
        normal = ParagraphStyle("body", fontName="Helvetica",
                                fontSize=11, leading=16,
                                textColor=colors.HexColor("#0F172A"))
        story  = []
        for line in text.split("\n"):
            if line.strip():
                story.append(Paragraph(line.replace("&","&amp;").replace("<","&lt;")
                                           .replace(">","&gt;"), normal))
            story.append(Spacer(1, 6))
        doc.build(story)
        return buf.getvalue()
    except ImportError:
        return None   # reportlab not installed — txt download only
    except Exception:
        return None
