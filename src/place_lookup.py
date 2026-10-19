import json
import re
from pathlib import Path

RAW = Path("data/raw")

STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "district of columbia": "DC", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "puerto rico": "PR",
}

# two-letter codes that are also common English words: match these by full name only
AMBIGUOUS_CODES = {"IN", "OR", "ME", "OK", "HI", "OH"}

INTENT = re.compile(
    r"places? of performance|performance locations?|locations? of (?:the )?(?:work|performance)"
    r"|work locations?|where (?:is|will|would|are) .{0,40}(?:performed|work)|performed (?:in|at)",
    re.I,
)


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def _describe(place):
    if not place:
        return ""
    if isinstance(place, dict):
        parts = []
        for key in ("streetAddress", "streetAddress2", "city", "state", "zip", "country"):
            v = place.get(key)
            if isinstance(v, dict):
                v = v.get("name") or v.get("code")
            if v:
                parts.append(str(v))
        if parts:
            return ", ".join(parts)
    return " ".join(_strings(place))


def _names(place, key):
    v = place.get(key) if isinstance(place, dict) else None
    if isinstance(v, dict):
        v = v.get("name")
    return str(v) if v else ""


def load():
    records = []
    if not RAW.exists():
        return records
    for folder in sorted(p for p in RAW.iterdir() if p.is_dir()):
        meta_file = folder / "metadata.json"
        if not meta_file.exists():
            continue
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        place = meta.get("placeOfPerformance")
        records.append(
            {
                "notice_id": folder.name,
                "title": meta.get("title", ""),
                "text": _describe(place),
                "blob": " ".join(_strings(place)) if place else "",
                "city": _names(place, "city"),
                "country": _names(place, "country"),
            }
        )
    return records


def _wanted(question, records):
    """Return a list of (label, test) for every place named in the question."""
    wanted = []
    for name, code in STATES.items():
        by_name = re.search(rf"\b{name}\b", question, re.I)
        by_code = code not in AMBIGUOUS_CODES and re.search(rf"\b{code}\b", question)
        if by_name or by_code:
            wanted.append(
                (
                    name.title(),
                    lambda r, n=name, c=code: bool(
                        re.search(rf"\b{n}\b", r["blob"], re.I) or re.search(rf"\b{c}\b", r["blob"])
                    ),
                )
            )
    # cities and countries are learned from the data itself
    seen = set()
    for r in records:
        for term in (r["city"], r["country"]):
            if len(term) >= 3 and term.lower() not in seen and re.search(
                rf"\b{re.escape(term)}\b", question, re.I
            ):
                seen.add(term.lower())
                wanted.append(
                    (term.title(), lambda x, t=term: bool(re.search(rf"\b{re.escape(t)}\b", x["blob"], re.I)))
                )
    return wanted


def _pseudo_meta(r):
    return {
        "title": r["title"],
        "notice_id": r["notice_id"],
        "file": "metadata.json",
        "page": "-",
        "section": "notice metadata",
    }


def answer(question, notice=None):
    """Answer place-of-performance questions from notice metadata.
    Returns (text, sources), or None if the question is about something else."""
    if not INTENT.search(question):
        return None

    records = load()
    if notice:
        records = [r for r in records if notice.lower() in r["title"].lower()]
    if not records:
        return None

    wanted = _wanted(question, records)
    empty = [r for r in records if not r["text"]]

    # nothing in the metadata to use: let the normal document search try
    if not wanted and len(empty) == len(records):
        return None

    lines = []
    if wanted:
        labels = " or ".join(label for label, _ in wanted)
        hits = [r for r in records if any(test(r) for _, test in wanted)]
        if hits:
            lines.append(f"Notices with a place of performance in {labels}:")
            for r in hits:
                lines.append(f"- {r['title'][:80]}: {r['text']}")
        else:
            lines.append(f"No notice in the dataset lists {labels} as its place of performance.")
        if empty:
            lines.append(
                f"\nNote: {len(empty)} of {len(records)} notices have no place of performance in "
                "their metadata (large multi-award contracts often have none), so the work "
                "location may only be described in the documents."
            )
        sources = [_pseudo_meta(r) for r in (hits or records)]
    else:
        lines.append("Place of performance by notice:")
        for r in records:
            lines.append(f"- {r['title'][:80]}: {r['text'] or 'not listed in the notice metadata'}")
        sources = [_pseudo_meta(r) for r in records]

    lines.append("\nSource: structured notice data from the SAM.gov API, not the document text.")


