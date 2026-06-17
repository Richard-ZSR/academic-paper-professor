from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
WORK_ROOT = Path.cwd()
DEFAULT_CONFIG = WORK_ROOT / "paper_batch_config.json"
DEFAULT_INDEX = WORK_ROOT / "paper_index.json"
DEFAULT_PARSER = SCRIPT_DIR / "paper_acquire_parse.py"


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_path(value: str | None, base_dir: Path) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else (base_dir / path).resolve()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "paper"


def paper_key(paper: dict) -> str:
    arxiv_id = paper.get("arxiv_id") or paper.get("paper")
    if arxiv_id:
        return f"arxiv:{str(arxiv_id).replace('arXiv:', '').strip().lower()}"
    doi = paper.get("doi")
    if doi:
        return f"doi:{str(doi).strip().lower()}"
    pdf_url = paper.get("pdf_url")
    if pdf_url:
        return f"pdf_url:{str(pdf_url).strip().lower()}"
    title = paper.get("title")
    if title:
        normalized_title = re.sub(r"\s+", " ", str(title).strip()).lower()
        return f"title:{normalized_title}"
    local_id = paper.get("local_id")
    if local_id:
        return f"local:{safe_name(str(local_id)).lower()}"
    raise ValueError(f"Paper entry lacks arxiv_id/paper/doi/pdf_url/title/local_id: {paper}")


def paper_label(paper: dict) -> str:
    if paper.get("local_id"):
        return safe_name(str(paper["local_id"]))
    arxiv_id = paper.get("arxiv_id") or paper.get("paper")
    if arxiv_id:
        return safe_name(str(arxiv_id).replace("arXiv:", "").strip())
    if paper.get("doi"):
        return safe_name(str(paper["doi"]))
    if paper.get("pdf_url"):
        return safe_name(Path(str(paper["pdf_url"]).split("?")[0]).stem)
    return safe_name(str(paper.get("title", "paper"))[:80])


def has_raw_data(paper_dir: Path) -> bool:
    return any(
        path.exists() and path.stat().st_size > 0
        for path in (
            paper_dir / "paper.pdf",
            paper_dir / "source.tar",
            paper_dir / "text" / "full_text.txt",
        )
    )


def has_parse(paper_dir: Path) -> bool:
    return (paper_dir / "manifest.json").exists() and (
        paper_dir / "text" / "full_text.txt"
    ).exists()


def build_parser_command(paper: dict, target_dir: Path, parser_path: Path, acquisition: dict) -> list[str]:
    cmd = [sys.executable, str(parser_path)]
    cmd.extend(["--label", paper_label(paper)])
    arxiv_id = paper.get("arxiv_id") or paper.get("paper")
    if arxiv_id:
        cmd.extend(["--paper", str(arxiv_id)])
    elif paper.get("pdf_url"):
        cmd.extend(["--pdf-url", str(paper["pdf_url"])])
    elif paper.get("local_pdf"):
        cmd.extend(["--pdf-url", str(paper["local_pdf"])])
    else:
        raise ValueError(f"Paper entry lacks an acquisition source: {paper}")

    cmd.extend(["--out", str(target_dir)])
    passthrough = {
        "max_render_pages": "--max-render-pages",
    }
    for key, flag in passthrough.items():
        if acquisition.get(key) is not None:
            cmd.extend([flag, str(acquisition[key])])
    return cmd


def paper_fingerprint(paper: dict) -> dict:
    return {
        "key": paper_key(paper),
        "label": paper_label(paper),
        "title": paper.get("title"),
        "arxiv_id": paper.get("arxiv_id") or paper.get("paper"),
        "doi": paper.get("doi"),
        "pdf_url": paper.get("pdf_url"),
        "rank": paper.get("rank"),
        "topic_fit": paper.get("topic_fit"),
    }


def update_index(index_path: Path, paper: dict, paper_dir: Path, config: dict) -> None:
    index = load_json(index_path, {"version": 1, "papers": {}})
    papers = index.setdefault("papers", {})
    key = paper_key(paper)
    now = datetime.now(timezone.utc).isoformat()
    entry = papers.setdefault(key, {})
    analyses = sorted(
        str(path.name)
        for path in paper_dir.glob("analysis*.md")
        if path.is_file()
    )
    entry.update(
        {
            **paper_fingerprint(paper),
            "paper_dir": str(paper_dir.resolve()),
            "raw_files": {
                "paper_pdf": str((paper_dir / "paper.pdf").resolve())
                if (paper_dir / "paper.pdf").exists()
                else None,
                "source_tar": str((paper_dir / "source.tar").resolve())
                if (paper_dir / "source.tar").exists()
                else None,
                "full_text": str((paper_dir / "text" / "full_text.txt").resolve())
                if (paper_dir / "text" / "full_text.txt").exists()
                else None,
            },
            "analysis_files": analyses,
            "last_seen_at": now,
            "last_batch": {
                "batch_name": config.get("batch_name"),
                "topic": config.get("topic"),
                "time_frame": config.get("time_frame"),
            },
        }
    )
    write_json(index_path, index)


def copy_index_hit(existing_dir: Path, destination_dir: Path) -> None:
    if destination_dir.exists():
        return
    shutil.copytree(existing_dir, destination_dir)


def write_selection_metadata(paper_dir: Path, paper: dict, config: dict, config_path: Path) -> None:
    payload = {
        **paper,
        "batch": {
            "name": config.get("batch_name"),
            "topic": config.get("topic"),
            "time_frame": config.get("time_frame"),
            "config_path": str(config_path),
        },
    }
    write_json(paper_dir / "selection_metadata.json", payload)


def write_duplicate_table(target_dir: Path, duplicates: list[dict]) -> None:
    if not duplicates:
        return
    rows = [
        "| Key | Title | Existing directory | Copied to |",
        "| --- | --- | --- | --- |",
    ]
    for item in duplicates:
        rows.append(
            "| {key} | {title} | `{source}` | `{target}` |".format(
                key=item["key"],
                title=(item.get("title") or "").replace("|", "\\|"),
                source=item["source"],
                target=item["target"],
            )
        )
    (target_dir / "DUPLICATES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


def create_missing_stub(paper_dir: Path, paper: dict, reason: str) -> Path:
    paper_dir.mkdir(parents=True, exist_ok=True)
    stub = paper_dir / "MISSING_RAW_DATA.md"
    stub.write_text(
        "\n".join(
            [
                "# Missing raw paper data",
                "",
                f"- Title: {paper.get('title', '')}",
                f"- Key: {paper_key(paper)}",
                f"- Expected directory: `{paper_dir}`",
                f"- Reason: {reason}",
                "",
                "Manual action required: place the paper PDF at `paper.pdf` or provide a complete parse directory, then rerun the acquisition script.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return stub


def write_missing_report(target_dir: Path, missing: list[dict]) -> None:
    rows = [
        "# Missing Paper Data",
        "",
        "The acquisition step stopped because at least one selected paper could not be downloaded or parsed.",
        "",
        "| Key | Title | Directory | Stub | Error |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in missing:
        rows.append(
            "| {key} | {title} | `{directory}` | `{stub}` | {error} |".format(
                key=item["key"],
                title=(item.get("title") or "").replace("|", "\\|"),
                directory=item["directory"],
                stub=item["stub"],
                error=str(item["error"]).replace("|", "\\|"),
            )
        )
    (target_dir / "MISSING_PAPERS.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


def clear_missing_stub(paper_dir: Path) -> None:
    stub = paper_dir / "MISSING_RAW_DATA.md"
    if stub.exists():
        stub.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Acquire a configured batch of selected papers.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Batch JSON config path.")
    parser.add_argument("--index", default=str(DEFAULT_INDEX), help="paper_index.json path.")
    parser.add_argument("--force", action="store_true", help="Re-parse even when parsed files exist.")
    parser.add_argument(
        "--reparse-keys",
        nargs="*",
        default=[],
        help="Specific paper keys or labels to reparse even when index hits exist.",
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config_dir = config_path.parent
    config = load_json(config_path, None)
    if not config:
        raise SystemExit(f"Config file not found or empty: {config_path}")

    target_dir = resolve_path(config.get("target_dir"), config_dir)
    if target_dir is None:
        root = resolve_path(config.get("root"), config_dir) or config_dir
        target_dir = root / str(config["batch_name"])
    target_dir.mkdir(parents=True, exist_ok=True)

    index_path = Path(args.index).resolve()
    index = load_json(index_path, {"version": 1, "papers": {}})
    indexed_papers = index.get("papers", {})
    acquisition = dict(config.get("acquisition") or {})
    parser_path = resolve_path(acquisition.get("parser"), config_dir) or DEFAULT_PARSER
    if not parser_path.exists():
        raise FileNotFoundError(f"paper_acquire_parse.py not found: {parser_path}")

    papers = config.get("papers") or []
    if not papers:
        raise ValueError("Config must contain a non-empty papers array.")

    duplicates: list[dict] = []
    missing: list[dict] = []
    reparse_keys = {item.lower() for item in args.reparse_keys}

    for paper in papers:
        key = paper_key(paper)
        label = paper_label(paper)
        paper_dir = target_dir / label
        hit = indexed_papers.get(key)
        should_reparse = args.force or key.lower() in reparse_keys or label.lower() in reparse_keys

        if hit and not should_reparse:
            source_dir = Path(hit.get("paper_dir", ""))
            if source_dir.exists():
                copy_index_hit(source_dir, paper_dir)
                write_selection_metadata(paper_dir, paper, config, config_path)
                update_index(index_path, paper, paper_dir, config)
                duplicates.append(
                    {
                        "key": key,
                        "title": paper.get("title") or hit.get("title"),
                        "source": str(source_dir),
                        "target": str(paper_dir),
                    }
                )
                print(f"index hit copied: {label}")
                continue

        if has_parse(paper_dir) and not should_reparse:
            print(f"skip existing parse: {label}")
            clear_missing_stub(paper_dir)
            write_selection_metadata(paper_dir, paper, config, config_path)
            update_index(index_path, paper, paper_dir, config)
            continue

        try:
            cmd = build_parser_command(paper, target_dir, parser_path, acquisition)
            print("acquire", label)
            subprocess.run(cmd, check=True)
        except Exception as exc:
            stub = create_missing_stub(paper_dir, paper, str(exc))
            missing.append(
                {
                    "key": key,
                    "title": paper.get("title"),
                    "directory": str(paper_dir),
                    "stub": str(stub),
                    "error": str(exc),
                }
            )
            continue

        if not has_raw_data(paper_dir):
            stub = create_missing_stub(paper_dir, paper, "parser completed but no raw PDF/source/text was found")
            missing.append(
                {
                    "key": key,
                    "title": paper.get("title"),
                    "directory": str(paper_dir),
                    "stub": str(stub),
                    "error": "no raw PDF/source/text",
                }
            )
            continue

        clear_missing_stub(paper_dir)
        write_selection_metadata(paper_dir, paper, config, config_path)
        update_index(index_path, paper, paper_dir, config)

    write_duplicate_table(target_dir, duplicates)
    if missing:
        write_missing_report(target_dir, missing)
        print(f"missing paper data: {target_dir / 'MISSING_PAPERS.md'}")
        raise SystemExit(2)

    if duplicates:
        print(f"duplicates copied: {target_dir / 'DUPLICATES.md'}")
        print("Stop before re-analysis unless the user explicitly names papers to re-read.")
    stale_missing_report = target_dir / "MISSING_PAPERS.md"
    if stale_missing_report.exists():
        stale_missing_report.unlink()
    print(f"done: {target_dir}")


if __name__ == "__main__":
    main()
