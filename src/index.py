import json
from pathlib import Path

import chromadb

IN_FILE = Path("data/processed/chunks.jsonl")
BATCH = 500

client = chromadb.PersistentClient(path="vectordb")

# start fresh each run so you never get duplicates
try:
    client.delete_collection("solicitations")
except Exception:
    pass
col = client.create_collection("solicitations", metadata={"hnsw:space": "cosine"})

ids, docs, metas = [], [], []


def flush():
    if ids:
        col.add(ids=ids, documents=docs, metadatas=metas)
        print(f"  indexed {col.count()} chunks so far")
        ids.clear()
        docs.clear()
        metas.clear()


with open(IN_FILE, encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        header = f"{rec['title']} | {rec['file'].replace('+', ' ')} | {rec['section']}"
        ids.append(rec["chunk_id"])
        docs.append(header + "\n" + rec["text"])
        metas.append(
            {
                k: rec[k]
                for k in (
                    "notice_id",
                    "title",
                    "agency",
                    "naics",
                    "due_date",
                    "file",
                    "page",
                    "section",
                )
            }
        )
        if len(ids) >= BATCH:
            flush()
    flush()

print(f"Done. Total chunks in index: {col.count()}")