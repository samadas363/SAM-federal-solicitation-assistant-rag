import csv
import sys
from collections import defaultdict

sys.path.insert(0, "src")
from rag import ask


def norm(s):
    return s.replace("+", " ").lower()


with open("tests/questions.csv", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

results = []
stats = defaultdict(lambda: {"n": 0, "retr": 0, "retr_n": 0, "ans": 0, "ans_n": 0})

for r in rows:
    qid = r.get("id") or "?"
    qtype = r.get("type") or "other"
    try:
        answer, mets = ask(
            r["question"],
            (r.get("notice") or None),
            (r.get("file") or None),
        )
    except Exception as e:
        print(f"{qid}: ERROR {e}")
        continue

    # retrieval check: did any retrieved chunk come from the expected file (and page)?
    retr = None
    expected_file = (r.get("expected_file") or "").strip()
    expected_page = (r.get("expected_page") or "").strip()
    if expected_file:
        retr = any(
            norm(expected_file) in norm(m["file"])
            and (not expected_page or str(m["page"]) == expected_page)
            for m in mets
        )

    # answer check
    low = answer.lower()
    if qtype == "negative":
        correct = "not found" in low
    else:
        kws = [k.strip().lower() for k in (r.get("answer_keywords") or "").split("|") if k.strip()]
        correct = all(k in low for k in kws) if kws else None  # None = not scored

    s = stats[qtype]
    s["n"] += 1
    if retr is not None:
        s["retr_n"] += 1
        s["retr"] += int(retr)
    if correct is not None:
        s["ans_n"] += 1
        s["ans"] += int(correct)

    results.append(
        {
            "id": qid,
            "type": qtype,
            "question": r["question"],
            "retrieved_ok": retr,
            "answer_ok": correct,
            "answer": answer.replace("\n", " "),
        }
    )
    print(f"{qid:5} retrieval={retr}  answer={correct}")

if results:
    with open("tests/results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)

print("\nSUMMARY BY TYPE")
for t, s in stats.items():
    retr = f"{s['retr']}/{s['retr_n']}" if s["retr_n"] else "n/a"
    ans = f"{s['ans']}/{s['ans_n']}" if s["ans_n"] else "n/a"
    print(f"{t:14} retrieval {retr:7} answers {ans}")
print("\nFull answers saved to tests/results.csv")