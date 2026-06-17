from __future__ import annotations

import argparse
import difflib
import html
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path


ARXIV_API = "https://export.arxiv.org/api/query"
HF_DAILY = "https://huggingface.co/api/daily_papers"
WORK_ROOT = Path.cwd()
DEFAULT_CONFIG = WORK_ROOT / "paper_batch_config.json"
DEFAULT_REPORT = WORK_ROOT / "paper_batch_id_validation.json"


def normalize_title(value: str | None) -> str:
    value = html.unescape(value or "").lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_arxiv_id(value: str | None) -> str:
    value = str(value or "").replace("arXiv:", "").strip().rstrip("/")
    value = value.rsplit("/", 1)[-1]
    return re.sub(r"v\d+$", "", value)


def title_score(left: str | None, right: str | None) -> float:
    a = normalize_title(left)
    b = normalize_title(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.96
    a_tokens = a.split()
    b_tokens = b.split()
    if set(a_tokens) == set(b_tokens):
        return 1.0
    token_sort_score = difflib.SequenceMatcher(None, " ".join(sorted(a_tokens)), " ".join(sorted(b_tokens))).ratio()
    overlap = len(set(a_tokens) & set(b_tokens)) / max(len(set(a_tokens) | set(b_tokens)), 1)
    return max(difflib.SequenceMatcher(None, a, b).ratio(), token_sort_score, overlap)


def request_text(url: str, timeout: int = 30) -> str:
    ctx = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def request_text_retries(url: str, retries: int = 2, timeout: int = 20) -> str:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return request_text(url, timeout=timeout)
        except Exception as exc:  # noqa: BLE001 - network failures are reported in validation output.
            last_error = exc
            if attempt < retries:
                time.sleep(2 + attempt)
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def load_json_url(url: str, retries: int = 2):
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return json.loads(request_text(url))
        except Exception as exc:  # noqa: BLE001 - report network/API failures clearly.
            last_error = exc
            if attempt < retries:
                time.sleep(2 + attempt)
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def parse_date(value: str) -> date:
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def get_arxiv_by_ids(ids: list[str]) -> dict[str, dict]:
    ids = [item for item in ids if item]
    if not ids:
        return {}
    found: dict[str, dict] = {}
    for offset in range(0, len(ids), 50):
        chunk = ids[offset : offset + 50]
        url = f"{ARXIV_API}?id_list={','.join(urllib.parse.quote(i) for i in chunk)}"
        try:
            text = request_text_retries(url, retries=1, timeout=20)
        except RuntimeError:
            for item in chunk:
                fallback = get_arxiv_abs_title(item)
                if fallback:
                    found[item] = fallback
            continue
        root = ET.fromstring(text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns):
            raw_id = entry.findtext("atom:id", default="", namespaces=ns).rstrip("/")
            arxiv_id = normalize_arxiv_id(raw_id)
            title = re.sub(r"\s+", " ", entry.findtext("atom:title", default="", namespaces=ns)).strip()
            found[arxiv_id] = {"id": arxiv_id, "title": title, "source": "arxiv_id"}
        for item in chunk:
            normalized = normalize_arxiv_id(item)
            if normalized not in found:
                fallback = get_arxiv_abs_title(item)
                if fallback:
                    found[normalized] = {
                        "id": normalized,
                        "title": fallback["title"],
                        "source": fallback.get("source", "arxiv_abs"),
                    }
    return found


def get_arxiv_abs_title(arxiv_id: str) -> dict | None:
    url = f"https://arxiv.org/abs/{urllib.parse.quote(arxiv_id)}"
    try:
        text = request_text_retries(url, retries=1, timeout=12)
    except RuntimeError:
        return None
    patterns = [
        r'<meta\s+name="citation_title"\s+content="([^"]+)"',
        r'<h1\s+class="title[^"]*">\s*<span[^>]*>Title:\s*</span>\s*(.*?)\s*</h1>',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.S | re.I)
        if match:
            title = re.sub(r"<[^>]+>", "", match.group(1))
            title = re.sub(r"\s+", " ", html.unescape(title)).strip()
            return {"id": arxiv_id, "title": title, "source": "arxiv_abs"}
    return None


def get_hf_daily(start: date, end: date) -> list[dict]:
    rows: list[dict] = []
    current = start
    while current <= end:
        url = f"{HF_DAILY}?date={current.isoformat()}"
        try:
            data = load_json_url(url)
        except RuntimeError:
            current += timedelta(days=1)
            continue
        if isinstance(data, dict):
            data = data.get("papers") or data.get("dailyPapers") or data.get("data") or []
        for item in data:
            paper = item.get("paper") or {}
            paper_id = paper.get("id")
            title = item.get("title") or paper.get("title")
            if paper_id and title:
                rows.append(
                    {
                        "id": paper_id,
                        "title": title,
                        "hf_url": f"https://huggingface.co/papers/{paper_id}",
                        "doi": f"https://doi.org/10.48550/arXiv.{paper_id}",
                        "published_at": item.get("publishedAt"),
                        "hf_daily_date": current.isoformat(),
                        "hf_comments": item.get("numComments"),
                        "source": "huggingface_daily",
                    }
                )
        current += timedelta(days=1)
    return rows


def search_hf_by_title(title: str, hf_rows: list[dict]) -> dict | None:
    if not hf_rows:
        return None
    ranked = sorted(
        ((title_score(title, row["title"]), row) for row in hf_rows),
        key=lambda item: item[0],
        reverse=True,
    )
    score, row = ranked[0]
    if score >= 0.72:
        return {**row, "score": round(score, 4)}
    return None


def search_arxiv_by_title(title: str) -> dict | None:
    tokens = [
        token
        for token in normalize_title(title).split()
        if len(token) >= 4 and token not in {"with", "from", "towards", "toward", "large", "models"}
    ][:6]
    if not tokens:
        return None
    query = "+AND+".join(f"ti:{urllib.parse.quote(token)}" for token in tokens)
    url = f"{ARXIV_API}?search_query={query}&start=0&max_results=10&sortBy=relevance&sortOrder=descending"
    try:
        text = request_text(url)
    except Exception:
        return None
    root = ET.fromstring(text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    candidates = []
    for entry in root.findall("atom:entry", ns):
        raw_id = entry.findtext("atom:id", default="", namespaces=ns).rstrip("/")
        paper_id = normalize_arxiv_id(raw_id)
        candidate_title = re.sub(r"\s+", " ", entry.findtext("atom:title", default="", namespaces=ns)).strip()
        candidates.append((title_score(title, candidate_title), paper_id, candidate_title))
    if not candidates:
        return None
    score, paper_id, candidate_title = max(candidates, key=lambda item: item[0])
    if score >= 0.92:
        return {
            "id": paper_id,
            "title": candidate_title,
            "hf_url": f"https://huggingface.co/papers/{paper_id}",
            "doi": f"https://doi.org/10.48550/arXiv.{paper_id}",
            "source": "arxiv_title_search",
            "score": round(score, 4),
        }
    return None


def paper_id(paper: dict) -> str:
    return normalize_arxiv_id(paper.get("arxiv_id") or paper.get("paper"))


def apply_match(paper: dict, match: dict) -> None:
    matched_id = normalize_arxiv_id(match["id"])
    paper["title"] = match["title"]
    paper["arxiv_id"] = matched_id
    paper["local_id"] = matched_id
    paper["doi"] = match.get("doi") or f"https://doi.org/10.48550/arXiv.{matched_id}"
    paper["hf_url"] = match.get("hf_url") or f"https://huggingface.co/papers/{matched_id}"
    for key in ("published_at", "hf_daily_date", "hf_comments"):
        if match.get(key) is not None:
            paper[key] = match[key]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and optionally repair batch paper title/id mappings.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="paper_batch_config.json path.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help="Validation report path.")
    parser.add_argument("--fix", action="store_true", help="Rewrite mismatched papers when a confident title match is found.")
    parser.add_argument("--threshold", type=float, default=0.82, help="Minimum title similarity for configured id/title to pass.")
    parser.add_argument("--skip-hf-daily", action="store_true", help="Skip Hugging Face Daily Papers repair lookup.")
    parser.add_argument(
        "--hf-daily-max-days",
        type=int,
        default=120,
        help="Maximum time-frame length for Hugging Face Daily Papers lookup; longer ranges use arXiv-only validation.",
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    report_path = Path(args.report).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    papers = config.get("papers") or []
    ids = [paper_id(paper) for paper in papers]
    time_frame = config.get("time_frame") or {}
    start = parse_date(time_frame.get("start") or date.today().isoformat())
    end = parse_date(time_frame.get("end") or start.isoformat())
    day_count = (end - start).days + 1
    hf_daily_skipped = args.skip_hf_daily or day_count > args.hf_daily_max_days
    hf_rows = [] if hf_daily_skipped else get_hf_daily(start, end)
    hf_by_id = {row["id"]: row for row in hf_rows}
    arxiv_by_id = get_arxiv_by_ids(ids)

    results = []
    unresolved = []
    repaired = []
    for index, paper in enumerate(papers, start=1):
        configured_id = paper_id(paper)
        configured_title = str(paper.get("title") or "").strip()
        arxiv_match = arxiv_by_id.get(configured_id)
        hf_id_match = hf_by_id.get(configured_id)
        arxiv_score = title_score(configured_title, (arxiv_match or {}).get("title"))
        hf_score = title_score(configured_title, (hf_id_match or {}).get("title"))
        score = max(arxiv_score, hf_score)
        status = "ok" if score >= args.threshold else "mismatch"
        result = {
            "rank": paper.get("rank", index),
            "configured_id": configured_id,
            "configured_title": configured_title,
            "arxiv_title_for_configured_id": (arxiv_match or {}).get("title"),
            "hf_title_for_configured_id": (hf_id_match or {}).get("title"),
            "configured_score": round(score, 4),
            "arxiv_score": round(arxiv_score, 4),
            "hf_score": round(hf_score, 4),
            "status": status,
            "repair": None,
        }
        if status == "mismatch":
            repair = search_hf_by_title(configured_title, hf_rows) or search_arxiv_by_title(configured_title)
            result["repair"] = repair
            if repair and args.fix:
                apply_match(paper, repair)
                repaired.append({"rank": result["rank"], "old_id": configured_id, "new_id": repair["id"]})
                result["status"] = "repaired"
            elif repair:
                unresolved.append(result)
            else:
                unresolved.append(result)
        results.append(result)

    if args.fix and repaired:
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "config": str(config_path),
        "threshold": args.threshold,
        "checked": len(results),
        "repaired": repaired,
        "unresolved_count": len(unresolved),
        "hf_daily_skipped": hf_daily_skipped,
        "hf_daily_day_count": day_count,
        "hf_daily_max_days": args.hf_daily_max_days,
        "results": results,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if unresolved:
        print(f"paper id/title validation failed; report: {report_path}", file=sys.stderr)
        for item in unresolved:
            repair = item.get("repair") or {}
            suggestion = f" suggested={repair.get('id')} {repair.get('title')}" if repair else " no confident repair"
            print(
                f"- rank {item['rank']} configured={item['configured_id']} score={item['configured_score']}{suggestion}",
                file=sys.stderr,
            )
        raise SystemExit(1)

    action = "repaired" if repaired else "validated"
    print(f"{action} {len(results)} paper id/title mappings; report: {report_path}")


if __name__ == "__main__":
    main()
