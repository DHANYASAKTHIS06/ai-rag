# 🎓 CampusCopilot

AI-powered multi-agent campus assistant with RAG, eligibility checking, planning, helpdesk, and application letter generation.

**Tech:** Streamlit · Anthropic Claude · ChromaDB · SQLite · PyMuPDF

## Quick Start (Local)

```bash
# 1. Clone & enter
git clone https://github.com/YOUR_USERNAME/campuscopilot.git
cd campuscopilot

# 2. Virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your API key
set ANTHROPIC_API_KEY=sk-ant-your-key     # Windows
# export ANTHROPIC_API_KEY=sk-ant-your-key # macOS/Linux

# 5. Run
streamlit run app.py
```

**Default login:** `admin` / `admin123` · `officer` / `officer123`

## Deploy to Render.com

See the step-by-step guide in `DEPLOY_RENDER.md`.

## Features

- 🤖 9 AI agents: Orchestrator, Knowledge, Eligibility, Planning, Verification, Revision, Recovery, Helpdesk, Application Letter
- 📚 RAG pipeline with citation-backed answers
- 🌐 Multilingual support (English, Tamil, Hindi, Telugu)
- 👥 Role-based dashboards: Student, Admin, Helpdesk Officer
- 🎫 Helpdesk ticket system with AI-suggested responses
- 📝 Application letter studio with PDF export
- 🔒 Secure authentication with PBKDF2 password hashing
- 📄 PDF upload, security scanning, and document indexing
"# campuscopilot" 
