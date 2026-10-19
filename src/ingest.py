import os
import re
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ["SAM_API_KEY"]

URL = "https://api.sam.gov/opportunities/v2/search"
RAW = Path("data/raw")
RAW.mkdir(parents=True, exist_ok=True)
SEARCH_FILE = RAW / "search_results.json"
MAX_OPPS = 5  # keep small to protect your daily quota


def search():
    # Use the saved copy if it exists, so we don't waste API calls
    if SEARCH_FILE.exists():
        print("Using saved search results")
        return json.loads(SEARCH_FILE.read_text(encoding="utf-8"))

    r = requests.get(
        URL,
        params={
            "api_key": API_KEY,
            "postedFrom": "09/01/2026",
            "postedTo": "10/17/2026",
            "ncode": "541512",
            "ptype": "o",
            "limit": 10,
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    SEARCH_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("Saved search results")
    return data


def download_attachments(opp):
    links = opp.get("resourceLinks") or []
    folder = RAW / opp["noticeId"]
    folder.mkdir(exist_ok=True)
    # save the notice details too
    (folder / "metadata.json").write_text(json.dumps(opp, indent=2), encoding="utf-8")

    for i, link in enumerate(links, start=1):
        if list(folder.glob(f"{i}_*")):
            print(f"  skip attachment {i} (already downloaded)")
            continue
        resp = requests.get(link, params={"api_key": API_KEY}, timeout=60)
        resp.raise_for_status()
        cd = resp.headers.get("Content-Disposition", "")
        match = re.findall(r'filename="?([^";]+)"?', cd)
        name = match[0] if match else "file"
        (folder / f"{i}_{name}").write_bytes(resp.content)
        print(f"  saved {i}_{name}")


def main():
    data = search()
    opps = data.get("opportunitiesData", [])[:MAX_OPPS]
    print(f"Found {len(opps)} opportunities")
    for opp in opps:
        print(opp["noticeId"], "-", opp["title"])
        download_attachments(opp)


if __name__ == "__main__":
    main()