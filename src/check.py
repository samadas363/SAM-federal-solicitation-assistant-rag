import json, collections

c = collections.Counter()
first = None
for line in open("data/processed/chunks.jsonl", encoding="utf-8"):
    rec = json.loads(line)
    c[rec["section"]] += 1
    first = first or rec

print(c.most_common())
print({k: first[k] for k in ("naics", "due_date", "agency")})