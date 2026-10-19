import json

NAME = "Joint+Venture"  # part of the file name to look for

found = 0
with open("data/processed/documents.jsonl", encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        if NAME.lower() in rec["file"].lower():
            found += 1
            print(rec["file"], "page", rec["page"], "-", len(rec["text"]), "chars")
            print("   ", rec["text"][:200].replace("\n", " "))

print(f"\n{found} matching pages in documents.jsonl")