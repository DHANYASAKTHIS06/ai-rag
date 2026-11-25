"""
CampusCopilot — Database layer
Handles SQLite persistence, authentication, sessions, documents, tasks, tickets, chat.
"""
import sqlite3, os, hashlib, secrets, datetime, json

DB = os.getenv("DATABASE_PATH", "data/campus.db")
os.makedirs(os.path.dirname(DB) if os.path.dirname(DB) else "data", exist_ok=True)

# ─── connection ────────────────────────────────────────────────────────────────
def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c

# ─── password helpers ───────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return f"{salt}:{dk.hex()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        salt, dk_hex = stored.split(":", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
        return secrets.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False

# ─── schema init ───────────────────────────────────────────────────────────────
def init():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            email         TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL DEFAULT 'student'
                         CHECK(role IN ('student','admin','officer')),
            full_name     TEXT DEFAULT '',
            department    TEXT DEFAULT '',
            semester      TEXT DEFAULT '',
            cgpa          TEXT DEFAULT '',
            family_income TEXT DEFAULT '',
            created_at    TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token      TEXT PRIMARY KEY,
            user_id    INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS documents (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT UNIQUE NOT NULL,
            file_path     TEXT DEFAULT '',
            page_count    INTEGER DEFAULT 0,
            chunk_count   INTEGER DEFAULT 0,
            indexed       INTEGER DEFAULT 0,
            security_scan TEXT DEFAULT 'pending',
            uploaded_by   INTEGER,
            uploaded_at   TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(uploaded_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS notices (
            name        TEXT PRIMARY KEY,
            text        TEXT,
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            uploaded_by INTEGER,
            FOREIGN KEY(uploaded_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            procedure   TEXT,
            step        TEXT,
            status      TEXT DEFAULT 'pending'
                        CHECK(status IN ('pending','done','blocked')),
            deadline    TEXT DEFAULT '',
            source      TEXT DEFAULT '',
            note        TEXT DEFAULT '',
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tickets (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL,
            subject          TEXT NOT NULL,
            description      TEXT DEFAULT '',
            status           TEXT DEFAULT 'open'
                             CHECK(status IN ('open','in_progress','resolved','closed')),
            ai_suggestion    TEXT DEFAULT '',
            officer_response TEXT DEFAULT '',
            assigned_officer INTEGER,
            created_at       TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at       TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id)          REFERENCES users(id),
            FOREIGN KEY(assigned_officer) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            question    TEXT,
            answer      TEXT,
            sources_json TEXT DEFAULT '[]',
            language    TEXT DEFAULT 'english',
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        # Seed default admin and officer if they don't exist
        _seed_defaults(c)

def _seed_defaults(c):
    admin_pw = os.getenv("ADMIN_PASSWORD", "admin123")
    officer_pw = os.getenv("OFFICER_PASSWORD", "officer123")
    defaults = [
        ("admin",   "admin@campuscopilot.edu",   admin_pw,   "admin",   "System Administrator"),
        ("officer", "officer@campuscopilot.edu", officer_pw, "officer", "Helpdesk Officer"),
    ]
    for username, email, pw, role, full_name in defaults:
        exists = c.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if not exists:
            c.execute(
                "INSERT INTO users(username,email,password_hash,role,full_name) VALUES(?,?,?,?,?)",
                (username, email, hash_password(pw), role, full_name)
            )

# ─── user management ────────────────────────────────────────────────────────────
def create_user(username, email, password, role="student",
                full_name="", department="", semester="", cgpa="", family_income=""):
    try:
        with conn() as c:
            c.execute(
                """INSERT INTO users
                   (username,email,password_hash,role,full_name,department,semester,cgpa,family_income)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (username.strip(), email.strip(), hash_password(password),
                 role, full_name, department, semester, cgpa, family_income)
            )
            return c.execute("SELECT last_insert_rowid()").fetchone()[0]
    except sqlite3.IntegrityError:
        return None

def get_user_by_username(username):
    with conn() as c:
        r = c.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
        return dict(r) if r else None

def get_user_by_id(uid):
    with conn() as c:
        r = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        return dict(r) if r else None

def authenticate(username, password):
    user = get_user_by_username(username)
    if user and verify_password(password, user["password_hash"]):
        return user
    return None

def update_user_profile(uid, full_name="", department="", semester="", cgpa="", family_income=""):
    with conn() as c:
        c.execute(
            """UPDATE users SET full_name=?,department=?,semester=?,cgpa=?,family_income=?
               WHERE id=?""",
            (full_name, department, semester, cgpa, family_income, uid)
        )

def get_all_users(role=None):
    with conn() as c:
        if role:
            rows = c.execute("SELECT * FROM users WHERE role=? ORDER BY created_at DESC", (role,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

def change_password(uid, new_password):
    with conn() as c:
        c.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(new_password), uid))

# ─── sessions ───────────────────────────────────────────────────────────────────
def create_session(user_id) -> str:
    token = secrets.token_urlsafe(32)
    expires = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat()
    with conn() as c:
        c.execute("INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)",
                  (token, user_id, expires))
    return token

def get_session(token) -> dict | None:
    if not token:
        return None
    with conn() as c:
        r = c.execute("""
            SELECT u.* FROM users u
            JOIN sessions s ON s.user_id = u.id
            WHERE s.token=? AND s.expires_at > ?
        """, (token, datetime.datetime.utcnow().isoformat())).fetchone()
        return dict(r) if r else None

def delete_session(token):
    with conn() as c:
        c.execute("DELETE FROM sessions WHERE token=?", (token,))

def cleanup_sessions():
    with conn() as c:
        c.execute("DELETE FROM sessions WHERE expires_at < ?",
                  (datetime.datetime.utcnow().isoformat(),))

# ─── documents ──────────────────────────────────────────────────────────────────
def save_document(name, file_path="", page_count=0, chunk_count=0, uploaded_by=None):
    with conn() as c:
        c.execute("""
            INSERT INTO documents(name,file_path,page_count,chunk_count,uploaded_by)
            VALUES(?,?,?,?,?)
            ON CONFLICT(name) DO UPDATE SET
              file_path=excluded.file_path,
              page_count=excluded.page_count,
              uploaded_by=excluded.uploaded_by,
              uploaded_at=CURRENT_TIMESTAMP
        """, (name, file_path, page_count, chunk_count, uploaded_by))

def get_documents():
    with conn() as c:
        return [dict(r) for r in
                c.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()]

def get_document(name):
    with conn() as c:
        r = c.execute("SELECT * FROM documents WHERE name=?", (name,)).fetchone()
        return dict(r) if r else None

def update_document(name, indexed=None, security_scan=None, chunk_count=None):
    updates, vals = [], []
    if indexed is not None:
        updates.append("indexed=?"); vals.append(int(indexed))
    if security_scan is not None:
        updates.append("security_scan=?"); vals.append(security_scan)
    if chunk_count is not None:
        updates.append("chunk_count=?"); vals.append(chunk_count)
    if updates:
        vals.append(name)
        with conn() as c:
            c.execute(f"UPDATE documents SET {','.join(updates)} WHERE name=?", vals)

def delete_document(name):
    with conn() as c:
        c.execute("DELETE FROM documents WHERE name=?", (name,))

# ─── notices ────────────────────────────────────────────────────────────────────
def get_notice(name):
    with conn() as c:
        r = c.execute("SELECT text FROM notices WHERE name=?", (name,)).fetchone()
        return r["text"] if r else None

def save_notice(name, text, uploaded_by=None):
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO notices(name,text,uploaded_by) VALUES(?,?,?)",
                  (name, text, uploaded_by))

# ─── tasks ───────────────────────────────────────────────────────────────────────
def add_tasks(user_id, procedure, steps):
    with conn() as c:
        for s in steps:
            c.execute(
                "INSERT INTO tasks(user_id,procedure,step,deadline,source) VALUES(?,?,?,?,?)",
                (user_id, procedure,
                 s.get("step", ""), s.get("deadline") or "", s.get("source") or "")
            )

def all_tasks(user_id):
    with conn() as c:
        return [dict(r) for r in
                c.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY procedure,id",
                          (user_id,)).fetchall()]

def set_status(tid, status, note=""):
    with conn() as c:
        c.execute("UPDATE tasks SET status=?,note=? WHERE id=?", (status, note, tid))

def delete_task(tid):
    with conn() as c:
        c.execute("DELETE FROM tasks WHERE id=?", (tid,))

# ─── helpdesk tickets ────────────────────────────────────────────────────────────
def create_ticket(user_id, subject, description=""):
    with conn() as c:
        c.execute(
            "INSERT INTO tickets(user_id,subject,description) VALUES(?,?,?)",
            (user_id, subject, description)
        )
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def get_tickets(user_id=None, status=None):
    with conn() as c:
        base = """
            SELECT t.*, u.full_name as student_name, u.username as student_username,
                   u.department, u.semester
            FROM tickets t JOIN users u ON t.user_id = u.id
        """
        conditions, vals = [], []
        if user_id is not None:
            conditions.append("t.user_id=?"); vals.append(user_id)
        if status is not None:
            conditions.append("t.status=?"); vals.append(status)
        if conditions:
            base += " WHERE " + " AND ".join(conditions)
        base += " ORDER BY t.created_at DESC"
        return [dict(r) for r in c.execute(base, vals).fetchall()]

def get_ticket(tid):
    with conn() as c:
        r = c.execute("""
            SELECT t.*, u.full_name as student_name, u.username as student_username,
                   u.department, u.semester, u.email as student_email
            FROM tickets t JOIN users u ON t.user_id = u.id
            WHERE t.id=?
        """, (tid,)).fetchone()
        return dict(r) if r else None

def update_ticket(tid, status=None, ai_suggestion=None, officer_response=None,
                  assigned_officer=None):
    updates, vals = [], []
    if status is not None:
        updates.append("status=?"); vals.append(status)
    if ai_suggestion is not None:
        updates.append("ai_suggestion=?"); vals.append(ai_suggestion)
    if officer_response is not None:
        updates.append("officer_response=?"); vals.append(officer_response)
    if assigned_officer is not None:
        updates.append("assigned_officer=?"); vals.append(assigned_officer)
    updates.append("updated_at=CURRENT_TIMESTAMP")
    if updates:
        vals.append(tid)
        with conn() as c:
            c.execute(f"UPDATE tickets SET {','.join(updates)} WHERE id=?", vals)

# ─── chat history ────────────────────────────────────────────────────────────────
def save_chat(user_id, question, answer, sources=None, language="english"):
    with conn() as c:
        c.execute(
            "INSERT INTO chat_history(user_id,question,answer,sources_json,language) VALUES(?,?,?,?,?)",
            (user_id, question, answer, json.dumps(sources or []), language)
        )

def get_chat_history(user_id, limit=20):
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM chat_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["sources"] = json.loads(d.get("sources_json", "[]"))
            except Exception:
                d["sources"] = []
            result.append(d)
        return list(reversed(result))

def delete_chat_history(user_id):
    with conn() as c:
        c.execute("DELETE FROM chat_history WHERE user_id=?", (user_id,))

# ─── statistics ──────────────────────────────────────────────────────────────────
def get_stats():
    with conn() as c:
        total_docs    = c.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        indexed_docs  = c.execute("SELECT COUNT(*) FROM documents WHERE indexed=1").fetchone()[0]
        total_students= c.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]
        total_tickets = c.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        open_tickets  = c.execute("SELECT COUNT(*) FROM tickets WHERE status='open'").fetchone()[0]
        total_chunks  = c.execute("SELECT SUM(chunk_count) FROM documents").fetchone()[0] or 0
    return {
        "total_documents": total_docs,
        "indexed_documents": indexed_docs,
        "total_students": total_students,
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "total_chunks": total_chunks,
    }
