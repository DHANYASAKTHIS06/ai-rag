import sqlite3, os
os.makedirs("data", exist_ok=True)
DB = "data/campus.db"

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT, procedure TEXT, step TEXT,
            status TEXT DEFAULT 'pending', deadline TEXT, source TEXT, note TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS notices(
            name TEXT PRIMARY KEY, text TEXT, uploaded TEXT DEFAULT CURRENT_TIMESTAMP)""")

def add_tasks(procedure, steps):
    with conn() as c:
        for s in steps:
            c.execute("INSERT INTO tasks(procedure,step,deadline,source) VALUES(?,?,?,?)",
                      (procedure, s.get("step", ""), s.get("deadline") or "", s.get("source") or ""))

def all_tasks():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM tasks ORDER BY procedure,id")]

def set_status(tid, status, note=""):
    with conn() as c:
        c.execute("UPDATE tasks SET status=?, note=? WHERE id=?", (status, note, tid))

def delete_task(tid):
    with conn() as c:
        c.execute("DELETE FROM tasks WHERE id=?", (tid,))

def get_notice(name):
    with conn() as c:
        r = c.execute("SELECT text FROM notices WHERE name=?", (name,)).fetchone()
        return r["text"] if r else None

def save_notice(name, text):
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO notices(name,text) VALUES(?,?)", (name, text))
