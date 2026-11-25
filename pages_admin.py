"""CampusCopilot — Admin Dashboard"""
import streamlit as st
import os
import db, rag, ui

def show(user: dict):
    ui.inject_css()
    ui.render_sidebar(user)
    ui.page_header("🏠 Admin Dashboard",
                   "Manage documents, users, and monitor CampusCopilot.")

    stats = db.get_stats()

    # ── Stats row ──────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [
        ("📄", "Documents",        stats["total_documents"],   str(stats["indexed_documents"]) + " indexed"),
        ("👥", "Students",         stats["total_students"],    "registered"),
        ("🎫", "Total Tickets",    stats["total_tickets"],     str(stats["open_tickets"]) + " open"),
        ("🔢", "Indexed Chunks",   stats["total_chunks"],      "in vector store"),
        ("✅", "Indexed Docs",     stats["indexed_documents"],
             f"of {stats['total_documents']} total"),
    ]
    for col, (icon, label, val, sub) in zip([c1,c2,c3,c4,c5], metrics):
        with col:
            st.markdown(f"""
            <div class="stat-card">
              <div class="stat-label">{icon} {label}</div>
              <div class="stat-value">{val}</div>
              <div class="stat-delta">{sub}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tab layout ─────────────────────────────────────────────────────────
    tab_docs, tab_upload, tab_users, tab_tickets = st.tabs(
        ["📄 Documents", "⬆️ Upload & Index", "👥 Students", "🎫 Tickets"]
    )

    # ── Documents tab ──────────────────────────────────────────────────────
    with tab_docs:
        docs = db.get_documents()
        if not docs:
            st.markdown("""
            <div class="cc-alert info">
              <span>ℹ️</span><span>No documents uploaded yet. Use the Upload tab.</span>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"**{len(docs)} document(s)** in the system")
            for doc in docs:
                scan = doc.get("security_scan", "pending")
                scan_badge = ui.status_badge(
                    "safe" if scan == "safe" else
                    ("unsafe" if scan == "unsafe" else "pending_scan")
                )
                indexed_badge = ui.badge("Indexed ✓", "green") if doc.get("indexed") else \
                                ui.badge("Not Indexed", "grey")
                st.markdown(f"""
                <div class="card" style="padding:1rem 1.25rem;margin-bottom:.6rem">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                      <div style="font-weight:600;font-size:.9rem;color:#0F172A">
                        📄 {doc['name']}
                      </div>
                      <div style="font-size:.78rem;color:#64748B;margin-top:.2rem">
                        {doc['page_count']} pages · {doc['chunk_count']} chunks ·
                        Uploaded {doc['uploaded_at'][:10]}
                      </div>
                    </div>
                    <div style="display:flex;gap:.5rem;align-items:center">
                      {scan_badge} {indexed_badge}
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)

                col1, col2 = st.columns([1, 5])
                with col1:
                    if st.button("🗑 Delete", key=f"del_doc_{doc['name']}",
                                 help="Delete document and its index"):
                        rag.delete_document(doc["name"])
                        db.delete_document(doc["name"])
                        st.success(f"Deleted {doc['name']}")
                        st.rerun()

    # ── Upload tab ─────────────────────────────────────────────────────────
    with tab_upload:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### Upload College PDF Documents")
        st.markdown('<p style="color:#475569;font-size:.88rem">'
                    'Upload scholarship notices, prospectus, fee schedules, '
                    'hostel rules, certificate procedures, etc.</p>',
                    unsafe_allow_html=True)

        files = st.file_uploader("Choose PDF files", type="pdf",
                                 accept_multiple_files=True,
                                 help="Max 50 MB per file")
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            do_scan  = st.checkbox("Security scan (prompt injection detection)", value=True)
        with col_opt2:
            do_index = st.checkbox("Index immediately after upload", value=True)

        if files:
            if st.button("⬆️ Upload & Process", type="primary", use_container_width=True):
                for f in files:
                    if f.size > 50 * 1024 * 1024:
                        st.error(f"⚠️ {f.name}: File too large (max 50 MB)")
                        continue

                    data = f.read()

                    with st.spinner(f"Processing {f.name}..."):
                        # Save file
                        file_path = rag.save_pdf(data, f.name)

                        # Extract
                        pages = rag.extract_pdf(data)
                        if not pages:
                            st.warning(f"⚠️ {f.name}: No extractable text. Skipping.")
                            continue

                        # Security scan
                        scan_result = "not_checked"
                        all_text    = " ".join(t for _, t in pages)
                        if do_scan:
                            sr = rag.security_scan(all_text)
                            scan_result = "safe" if sr["safe"] else "unsafe"
                            if not sr["safe"]:
                                st.error(f"🚨 {f.name}: SECURITY ALERT — Suspicious content detected!")
                                for issue in sr["issues"]:
                                    st.markdown(f"  - {issue}")
                                st.warning("Document quarantined. It was NOT indexed.")
                                db.save_document(f.name, file_path, len(pages), 0,
                                                 uploaded_by=user["id"])
                                db.update_document(f.name, security_scan="unsafe", indexed=False)
                                # Save notice text anyway
                                db.save_notice(f.name, all_text, uploaded_by=user["id"])
                                continue

                        # Check for changes
                        old_text = db.get_notice(f.name)
                        if old_text and old_text != all_text:
                            diffs = rag.diff_text(old_text, all_text)
                            if diffs:
                                st.info(f"📢 {f.name}: Document updated — {len(diffs)} line(s) changed.")

                        # Save to DB
                        db.save_notice(f.name, all_text, uploaded_by=user["id"])
                        db.save_document(f.name, file_path, len(pages), 0,
                                         uploaded_by=user["id"])
                        db.update_document(f.name, security_scan=scan_result)

                        # Index
                        chunk_count = 0
                        if do_index:
                            chunk_count = rag.ingest(f.name, pages)
                            db.update_document(f.name, indexed=True, chunk_count=chunk_count)
                            st.success(f"✅ {f.name}: {chunk_count} chunks indexed "
                                       f"({len(pages)} pages)")
                        else:
                            st.success(f"✅ {f.name}: Uploaded ({len(pages)} pages). "
                                       "Index it manually when ready.")

        st.markdown('</div>', unsafe_allow_html=True)

        # Re-index existing unindexed docs
        docs = db.get_documents()
        unindexed = [d for d in docs if not d.get("indexed") and d.get("security_scan") != "unsafe"]
        if unindexed:
            st.markdown("### 🔄 Re-index Documents")
            for doc in unindexed:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"📄 **{doc['name']}** — not yet indexed")
                with col2:
                    if st.button("Index", key=f"idx_{doc['name']}"):
                        fp = doc.get("file_path", "")
                        if fp and os.path.exists(fp):
                            with open(fp, "rb") as fh:
                                data = fh.read()
                            pages = rag.extract_pdf(data)
                            if pages:
                                cnt = rag.ingest(doc["name"], pages)
                                db.update_document(doc["name"], indexed=True, chunk_count=cnt)
                                st.success(f"Indexed: {cnt} chunks")
                                st.rerun()
                        else:
                            st.error("Original file not found. Please re-upload.")

    # ── Users tab ──────────────────────────────────────────────────────────
    with tab_users:
        students = db.get_all_users(role="student")
        st.markdown(f"**{len(students)} student(s)** registered")
        if students:
            st.markdown('<table class="cc-table"><thead><tr>'
                        '<th>Name</th><th>Username</th><th>Department</th>'
                        '<th>Semester</th><th>CGPA</th><th>Registered</th>'
                        '</tr></thead><tbody>', unsafe_allow_html=True)
            for s in students:
                st.markdown(f"""<tr>
                  <td>{s.get('full_name','—')}</td>
                  <td><code>{s['username']}</code></td>
                  <td>{s.get('department','—')}</td>
                  <td>{s.get('semester','—')}</td>
                  <td>{s.get('cgpa','—')}</td>
                  <td>{s.get('created_at','')[:10]}</td>
                </tr>""", unsafe_allow_html=True)
            st.markdown("</tbody></table>", unsafe_allow_html=True)

    # ── Tickets tab ────────────────────────────────────────────────────────
    with tab_tickets:
        all_tickets = db.get_tickets()
        if not all_tickets:
            st.info("No tickets submitted yet.")
        else:
            for t in all_tickets:
                badge_html = ui.status_badge(t["status"])
                st.markdown(f"""
                <div class="ticket-card">
                  <div style="display:flex;justify-content:space-between">
                    <div>
                      <strong>#{t['id']}</strong> — {t['subject']}
                      <span style="margin-left:.75rem;font-size:.8rem;color:#64748B">
                        from {t.get('student_name') or t.get('student_username','?')}
                        ({t.get('department','')})
                      </span>
                    </div>
                    {badge_html}
                  </div>
                  <div style="font-size:.82rem;color:#334155;margin-top:.4rem">
                    {t.get('description','')[:100]}
                  </div>
                </div>""", unsafe_allow_html=True)
