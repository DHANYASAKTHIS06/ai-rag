# CampusCopilot
RAG + LangGraph multi-agent campus assistant (Streamlit).

## Run locally
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key                   # Windows: set ANTHROPIC_API_KEY=your_key
streamlit run app.py

## Docker
docker build -t campuscopilot .
docker run -p 8501:8501 -e ANTHROPIC_API_KEY=your_key -v $(pwd)/data:/app/data campuscopilot
"# ai-rag" 
