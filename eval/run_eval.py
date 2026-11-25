"""
CampusCopilot — Evaluation Framework
Usage:
  python eval/run_eval.py --mode retrieval
  python eval/run_eval.py --mode full --limit 10
"""
import sys, os, json, argparse, datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import rag, agents

QUESTIONS_FILE = os.path.join(os.path.dirname(__file__), "questions.json")

def load_questions(limit=None):
    with open(QUESTIONS_FILE) as f:
        qs = json.load(f)
    return qs[:limit] if limit else qs

def eval_retrieval(questions):
    """Test: does retrieval return any chunks for each question?"""
    print("\n" + "="*60)
    print("RETRIEVAL EVALUATION")
    print("="*60)
    total = 0; hits = 0
    for q in questions:
        if not q.get("requires_docs"):
            continue
        total += 1
        chunks = rag.search(q["question"], k=5)
        hit = len(chunks) > 0
        if hit:
            hits += 1
            # Check topic coverage
            text_lower = " ".join(c["text"].lower() for c in chunks)
            covered = [t for t in q.get("expected_topics",[]) if t in text_lower]
        else:
            covered = []
        status = "✅ HIT" if hit else "❌ MISS"
        print(f"\n[{q['id']}] {status}")
        print(f"  Q: {q['question'][:70]}")
        print(f"  Chunks: {len(chunks)}, Topics covered: {covered}")
        if chunks:
            print(f"  Sources: {list({c['source'] for c in chunks})}")
    print(f"\nRetrieval: {hits}/{total} questions returned results")
    return {"total": total, "hits": hits}

def eval_full(questions, limit=None):
    """Test: full pipeline — retrieval + answer + verification."""
    print("\n" + "="*60)
    print("FULL PIPELINE EVALUATION")
    print("="*60)
    results = []
    qs = questions[:limit] if limit else questions
    for q in qs:
        print(f"\n[{q['id']}] {q['question'][:70]}")
        try:
            result = agents.run(q["question"])
        except Exception as e:
            print(f"  ❌ PIPELINE ERROR: {e}")
            results.append({"id": q["id"], "error": str(e)})
            continue

        answer  = result.get("answer", "")
        ver     = result.get("verification", {})
        chunks  = result.get("chunks", [])
        lang    = result.get("language", "english")

        # Checks
        no_docs   = "No documents" in answer or len(chunks) == 0
        verified  = ver.get("verified", True) if ver else True
        has_cite  = "[1]" in answer or "[2]" in answer or len(chunks) == 0

        if q.get("unanswerable") and not no_docs:
            status = "⚠️  SHOULD HAVE SAID NO DOCS" if len(chunks) == 0 else "✅ ANSWERED (check manually)"
        elif no_docs and q.get("requires_docs"):
            status = "⚠️  NO DOCS — upload college documents to test properly"
        elif not verified:
            issues = ver.get("issues", [])
            status = f"⚠️  VERIFICATION ISSUES: {issues[:2]}"
        elif q.get("language") and lang != q["language"]:
            status = f"⚠️  WRONG LANGUAGE: got {lang}, expected {q['language']}"
        else:
            status = "✅ PASS"

        print(f"  Status:   {status}")
        print(f"  Language: {lang}")
        print(f"  Chunks:   {len(chunks)}")
        print(f"  Verified: {verified}")
        print(f"  Has cite: {has_cite}")
        print(f"  Answer:   {answer[:120]}...")

        results.append({
            "id":       q["id"],
            "status":   status,
            "chunks":   len(chunks),
            "verified": verified,
            "language": lang,
        })

    passed = sum(1 for r in results if "PASS" in r.get("status", ""))
    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{len(results)} passed")
    print(f"{'='*60}\n")
    return results

def main():
    parser = argparse.ArgumentParser(description="CampusCopilot Evaluation")
    parser.add_argument("--mode",  choices=["retrieval", "full"], default="retrieval")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max questions to evaluate (full mode)")
    args = parser.parse_args()

    questions = load_questions()
    print(f"Loaded {len(questions)} evaluation questions")
    print(f"ChromaDB chunks: {rag.count()}")
    print(f"Timestamp: {datetime.datetime.now().isoformat()}")

    if args.mode == "retrieval":
        eval_retrieval(questions)
    else:
        eval_full(questions, args.limit)

if __name__ == "__main__":
    main()
