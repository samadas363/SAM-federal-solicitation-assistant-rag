import json
import re
from collections import defaultdict
from pathlib import Path

IN_FILE = Path("data/processed/documents.jsonl")
OUT_FILE = Path("data/processed/chunks.jsonl")

CHUNK_WORDS = 250   # target chunk size
OVERLAP = 40        # words shared between neighboring chunks

# Matches headings like "SECTION L - INSTRUCTIONS..." at the start of a line.
# Case-sensitive on purpose, so sentences like "see Section L" don't match.
SECTION_RE = re.compile(r"^\s*SECTION\s+([A-M])\b", re.MULTILINE)


def split_words(text, size, overlap):
    words = text.split()
    if len(words) <= size:
        return [" ".join(words)]
    chunks, step = [], size - overlap
    for start in range(0, len(words), step):
        piece = words[start:start + size]
        chunks.append(" ".join(piece))
        if start + size >= len(words):
            break
    return chunks


def main():
    # group pages by file, in page order
    files = defaultdict(list)
    with open(IN_FILE, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            files[(rec["notice_id"], rec["file"])].append(rec)

    total = 0
    sections_found = 0
    word_counts = []

    with open(OUT_FILE, "w", encoding="utf-8") as out:
        for (notice_id, fname), pages in files.items():
            pages.sort(key=lambda r: r["page"])
            section = ""  # carries forward until a new heading appears

            for rec in pages:
                matches = SECTION_RE.findall(rec["text"])
                if matches:
                    section = f"Section {matches[-1]}"
                    sections_found += 1

                for n, piece in enumerate(split_words(rec["text"], CHUNK_WORDS, OVERLAP)):
                    chunk = {
                        "chunk_id": f"{notice_id}:{fname}:p{rec['page']}:{n}",
                        "notice_id": notice_id,
                        "title": rec["title"],
                        "agency": rec["agency"],
                        "naics": rec["naics"],
                        "due_date": rec["due_date"],
                        "file": fname,
                        "page": rec["page"],
                        "section": section,
                        "text": piece,
                    }
                    out.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                    total += 1
                    word_counts.append(len(piece.split()))

    avg = sum(word_counts) / max(len(word_counts), 1)
    print(f"Created {total} chunks (average {avg:.0f} words)")
    print(f"Section headings detected on {sections_found} pages")
    print(f"Saved to {OUT_FILE}")


if __name__ == "__main__":
    main()