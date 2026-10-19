import re

import chromadb
from anthropic import Anthropic
from dotenv import load_dotenv

import place_lookup

load_dotenv()
llm = Anthropic()  # reads ANTHROPIC_API_KEY from .env
MODEL = "claude-haiku-5-5"

col = chromadb.PersistentClient(path="vectordb").get_collection("solicitations")
_metas = col.get(include=["metadatas"])["metadatas"]

SYSTEM = (
    "You answer questions about US federal solicitations using ONLY the numbered "
    "excerpts provided. After each claim, cite the excerpt number like [2]. "
    "Keep the answer under 200 words and finish every sentence. "
    "If the excerpts do not contain the answer, reply exactly: "
    "'Not found in the retrieved documents.' Do not use outside knowledge."
)


def _where(notice, file):
    conds = []
    if notice:
        ids = sorted({m["notice_id"] for m in _metas if notice.lower() in m["title"].lower()})
        if not ids:
            raise ValueError(f"No notice title contains '{notice}'")
        conds.append({"notice_id": {"$in": ids}})
    if file:
        files = sorted({m["file"] for m in _metas if file.lower() in m["file"].lower()})
        if not files:
            raise ValueError(f"No file name contains '{file}'")
        conds.append({"file": {"$in": files}})
    if not conds:
        return None
    return conds[0] if len(conds) == 1 else {"$and": conds}


def _key(doc):
    # compare passages by their letters only, so version numbers, dates and
    # page headers that differ between amendments don't hide duplicates
    body = doc.split("\n", 1)[-1]
    letters = re.sub(r"[^a-z]", "", body.lower())
    return letters[100:400] or letters


def retrieve(question, notice=None, file=None, k=6):
    if file and k == 6:
        k = 10  # a file filter narrows the search, so show more of it
    res = col.query(query_texts=[question], n_results=k * 4, where=_where(notice, file))
    docs, mets = [], []
    seen = set()
    for doc, m in zip(res["documents"][0], res["metadatas"][0]):
        key = _key(doc)
        if key in seen:
            continue
        seen.add(key)
        docs.append(doc)
        mets.append(m)
        if len(docs) == k:
            break
    return docs, mets


def ask(question, notice=None, file=None, k=6):
    # structured questions (place of performance) are answered from notice metadata
    structured = place_lookup.answer(question, notice)
    if structured is not None:
        return structured

    docs, mets = retrieve(question, notice, file, k)

    context = ""
    for i, (doc, m) in enumerate(zip(docs, mets), start=1):
        name = m["file"].replace("+", " ")
        context += f"[{i}] {m['title'][:60]} | {name} | page {m['page']}\n{doc}\n\n"

    msg = llm.messages.create(
        model=MODEL,
        max_tokens=3000,
        system=SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Excerpts:\n\n{context}\nQuestion: {question}",
            }
        ],
    )

    # keep only the text blocks; skip thinking blocks
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    if not text.strip():
        text = "(The model returned no text. Try again or raise max_tokens.)"
    return text, mets