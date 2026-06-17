from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import acquire_papers


SCRIPT_DIR = Path(__file__).resolve().parent
WORK_ROOT = Path.cwd()
DEFAULT_INDEX = WORK_ROOT / "paper_index.json"
DEFAULT_PARSER = SCRIPT_DIR / "paper_acquire_parse.py"


def load_paper_from_args(args: argparse.Namespace) -> dict:
    if args.paper_json:
        path = Path(args.paper_json).resolve()
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            if len(data) != 1:
                raise ValueError("--paper-json must contain exactly one paper for selected acquisition")
            return data[0]
        return data

    paper: dict = {
        "title": args.title,
        "arxiv_id": args.arxiv_id,
        "pdf_url": args.pdf_url,
        "local_pdf": args.local_pdf,
        "doi": args.doi,
        "local_id": args.local_id,
        "selection_reason": args.selection_reason,
    }
    return {key: value for key, value in paper.items() if value is not None}


def latest_analysis(paper_dir: Path) -> Path | None:
    candidates = sorted(
        (path for path in paper_dir.glob("analysis*.md") if path.is_file()),
        key=lambda path: (path.stat().st_mtime, path.name),
        reverse=True,
    )
    return candidates[0] if candidates else None


def write_single_metadata(paper_dir: Path, paper: dict) -> None:
    payload = {
        **paper,
        "single_selection": {
            "selected_at": datetime.now(timezone.utc).isoformat(),
            "source": "user filename or model-selected paper",
        },
    }
    acquire_papers.write_json(paper_dir / "selection_metadata.json", payload)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Acquire one user-specified or model-selected academic paper."
    )
    parser.add_argument("--paper-json", help="JSON file containing one selected paper object.")
    parser.add_argument("--title")
    parser.add_argument("--arxiv-id")
    parser.add_argument("--pdf-url")
    parser.add_argument("--local-pdf")
    parser.add_argument("--doi")
    parser.add_argument("--local-id")
    parser.add_argument("--selection-reason")
    parser.add_argument("--out", default=str(WORK_ROOT / "papers"), help="Output root for selected papers.")
    parser.add_argument("--index", default=str(DEFAULT_INDEX), help="paper_index.json path.")
    parser.add_argument("--force", action="store_true", help="Acquire even when index already contains this paper.")
    parser.add_argument("--max-render-pages", type=int, default=10)
    parser.add_argument("--parser", default=str(DEFAULT_PARSER))
    args = parser.parse_args()

    paper = load_paper_from_args(args)
    key = acquire_papers.paper_key(paper)
    label = acquire_papers.paper_label(paper)
    out_dir = Path(args.out).resolve()
    paper_dir = out_dir / label
    index_path = Path(args.index).resolve()
    index = acquire_papers.load_json(index_path, {"version": 1, "papers": {}})
    hit = (index.get("papers") or {}).get(key)

    if hit and not args.force:
        existing_dir = Path(hit.get("paper_dir", ""))
        latest = latest_analysis(existing_dir) if existing_dir.exists() else None
        print(f"INDEX_HIT {key}")
        print(f"existing_dir={existing_dir}")
        if latest:
            print(f"latest_analysis={latest}")
        print("Ask the user: repeat parsing, or deep-read the existing/latest analysis?")
        return

    acquisition = {
        "max_render_pages": args.max_render_pages,
    }
    parser_path = Path(args.parser).resolve()
    paper_dir.mkdir(parents=True, exist_ok=True)
    try:
        cmd = acquire_papers.build_parser_command(paper, out_dir, parser_path, acquisition)
        print("acquire", label)
        subprocess.run(cmd, check=True)
    except Exception as exc:
        stub = acquire_papers.create_missing_stub(paper_dir, paper, str(exc))
        acquire_papers.write_missing_report(
            out_dir,
            [
                {
                    "key": key,
                    "title": paper.get("title"),
                    "directory": str(paper_dir),
                    "stub": str(stub),
                    "error": str(exc),
                }
            ],
        )
        print(f"missing paper data: {out_dir / 'MISSING_PAPERS.md'}")
        raise SystemExit(2)

    if not acquire_papers.has_raw_data(paper_dir):
        stub = acquire_papers.create_missing_stub(
            paper_dir, paper, "parser completed but no raw PDF/source/text was found"
        )
        acquire_papers.write_missing_report(
            out_dir,
            [
                {
                    "key": key,
                    "title": paper.get("title"),
                    "directory": str(paper_dir),
                    "stub": str(stub),
                    "error": "no raw PDF/source/text",
                }
            ],
        )
        raise SystemExit(2)

    write_single_metadata(paper_dir, paper)
    acquire_papers.update_index(
        index_path,
        paper,
        paper_dir,
        {
            "batch_name": "single-paper",
            "topic": paper.get("topic_fit") or paper.get("selection_reason"),
            "time_frame": None,
        },
    )
    print(f"done: {paper_dir}")


if __name__ == "__main__":
    main()
