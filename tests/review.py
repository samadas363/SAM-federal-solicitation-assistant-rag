import csv
import sys

sys.path.insert(0, "src")
from rag import ask

with open("tests/questions.csv", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

for r in rows:
    if (r.get("expected_file") or "").strip() and (r.get("answer_keywords") or "").strip():
        continue  # already filled in
    if r["type"] == "negative":
        continue
    print("=" * 70)
    print(f"{r['id']}  [{r['type']}]  {r['question']}")
    print(f"filters: notice={r['notice'] or '-'}  file={r['file'] or '-'}")
    try:
        answer, mets = ask(r["question"], r["notice"] or None, r["file"] or None)
    except Exception as e:
        print("ERROR", e)
        continue
    print("\nANSWER:", answer)
    print("\nSOURCES:")
    for i, m in enumerate(mets, start=1):
        print(f"  [{i}] {m['file']}  page {m['page']}")