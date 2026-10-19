import hashlib
import re

import chromadb
from anthropic import Anthropic

from upload_reader import read_uploaded_file


MODEL = "claude-haiku-5-5"
CHUNK_WORDS = 250
OVERLAP = 40
MAX_FILE_BYTES = 20 * 1024 * 1024

SYSTEM = (
    "You answer questions about a user-uploaded solicitation using ONLY "
    "the numbered excerpts provided. Cite each factual claim with excerpt "
    "numbers like [1]. Keep answers concise. If the excerpts do not contain "
    "the answer, reply exactly: "
    "'Not found in the uploaded document.' Do not use outside knowledge."
)


def split_text(text):
    words = text.split()
    if not words:
        return []

    if len(words) <= CHUNK_WORDS:
        return [text]

    chunks = []
    step = CHUNK_WORDS - OVERLAP

    for start in range(0, len(words), step):
        chunk = " ".join(words[start:start + CHUNK_WORDS])
        chunks.append(chunk)

        if start + CHUNK_WORDS >= len(words):
            break

    return chunks


def build_index(filename, data):
    if not data:
        raise ValueError("The uploaded file is empty.")

    if len(data) > MAX_FILE_BYTES:
        raise ValueError("Please upload a file smaller than 20 MB.")

    pages = read_uploaded_file(filename, data)

    client = chromadb.EphemeralClient()
    collection = client.create_collection(
        name="uploaded_solicitation",
        metadata={"hnsw:space": "cosine"},
    )

    ids = []
    documents = []
    metadatas = []

    for page_number, text in pages:
        for chunk_number, chunk in enumerate(split_text(text)):
            ids.append(f"page-{page_number}-chunk-{chunk_number}")
            documents.append(chunk)
            metadatas.append({
                "filename": filename,
                "page": int(page_number),
                "chunk": int(chunk_number),
            })

    if not documents:
        raise ValueError(
            "No readable text was found. The file may be scanned or empty."
        )

    for start in range(0, len(documents), 500):
        collection.add(
            ids=ids[start:start + 500],
            documents=documents[start:start + 500],
            metadatas=metadatas[start:start + 500],
        )

    fingerprint = hashlib.sha256(data).hexdigest()

    return {
        "client": client,
        "collection": collection,
        "fingerprint": fingerprint,
        "filename": filename,
        "chunks": len(documents),
    }


def answer_question(index, question, api_key, k=5):
    collection = index["collection"]
    count = collection.count()

    if count == 0:
        raise ValueError("The document has no searchable text.")

    results = collection.query(
        query_texts=[question],
        n_results=min(k, count),
    )

    docs = results["documents"][0]
    metadatas = results["metadatas"][0]

    excerpts = []
    for i, (doc, meta) in enumerate(zip(docs, metadatas), start=1):
        excerpts.append(
            f"[{i}] File: {meta['filename']} | Page: {meta['page']}\n{doc}"
        )

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=1200,
        system=SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                "Retrieved excerpts:\n\n"
                + "\n\n".join(excerpts)
                + f"\n\nQuestion: {question}"
            ),
        }],
    )

    text = "".join(
        block.text
        for block in response.content
        if getattr(block, "type", "") == "text"
    ).strip()

    if not text:
        text = "The model returned no text. Please try again."

    sources = [
        {
            "number": i,
            "filename": meta["filename"],
            "page": meta["page"],
        }
        for i, meta in enumerate(metadatas, start=1)
    ]

    return text, sources