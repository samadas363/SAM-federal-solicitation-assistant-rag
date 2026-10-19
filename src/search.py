import sys
import chromadb

col = chromadb.PersistentClient(path="vectordb").get_collection("solicitations")
query = " ".join(sys.argv[1:]) or "What are the past performance requirements?"

res = col.query(query_texts=[query], n_results=5)
for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
    print(f"[{dist:.3f}] {meta['title'][:40]} | {meta['file']} p{meta['page']} | {meta['section']}")
    print("   ", doc[:200].replace("\n", " "), "\n")