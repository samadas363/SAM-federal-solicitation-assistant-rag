import argparse
from rag import ask

ap = argparse.ArgumentParser()
ap.add_argument("question", nargs="+")
ap.add_argument("--notice")
ap.add_argument("--file")
ap.add_argument("-k", type=int, default=6)
a = ap.parse_args()

answer, mets = ask(" ".join(a.question), a.notice, a.file, a.k)
print("\nANSWER\n" + answer + "\n\nSOURCES")
for i, m in enumerate(mets, start=1):
    print(f"[{i}] {m['title'][:40]} | {m['file']} | page {m['page']}")