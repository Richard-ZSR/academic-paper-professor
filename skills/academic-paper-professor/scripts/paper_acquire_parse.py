#!/usr/bin/env python
"""Acquire and lightly parse academic paper sources for professor-style reading.

Supports arXiv IDs and direct PDF URLs. It writes raw sources plus a manifest
with extracted text paths and rendered page images. Layout-aware OCR/parsing is
handled separately by MinerU via execute_mineru.py.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tarfile
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "paper"


def download(url: str, target: Path, retries: int = 3) -> None:
    if target.exists() and target.stat().st_size > 0:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    partial = target.with_suffix(target.suffix + ".part")
    for attempt in range(retries + 1):
        try:
            with requests.get(url, stream=True, timeout=(20, 120)) as response:
                response.raise_for_status()
                with partial.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            handle.write(chunk)
            partial.replace(target)
            return
        except Exception as exc:  # noqa: BLE001 - acquisition reports the final download failure.
            last_error = exc
            if partial.exists():
                partial.unlink()
            if attempt < retries:
                time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"failed to download {url}: {last_error}")


def acquire_pdf(value: str, target: Path) -> None:
    parsed = urlparse(value)
    if parsed.scheme in ("http", "https"):
        download(value, target)
        return
    if parsed.scheme == "file":
        source = Path(unquote(parsed.path.lstrip("/")))
    else:
        source = Path(value)
    if not source.exists():
        raise FileNotFoundError(f"PDF path not found: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def arxiv_urls(identifier: str) -> tuple[str, str]:
    clean = identifier.replace("arXiv:", "").strip()
    return f"https://arxiv.org/e-print/{clean}", f"https://arxiv.org/pdf/{clean}.pdf"


def extract_source(archive_path: Path, out_dir: Path) -> list[str]:
    source_dir = out_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(archive_path) as tar:
            tar.extractall(source_dir)
    except tarfile.TarError:
        return []
    return [str(p.relative_to(out_dir)) for p in source_dir.rglob("*.tex")]


def extract_pdf(pdf_path: Path, out_dir: Path, max_render_pages: int) -> dict:
    import fitz

    text_dir = out_dir / "text"
    image_dir = out_dir / "rendered_pages"
    text_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    all_text = []
    rendered = []
    figure_like = []

    for index, page in enumerate(doc):
        text = page.get_text("text")
        all_text.append(f"\n\n--- page {index + 1} ---\n{text}")
        if re.search(r"\b(fig\.?|figure|table|tab\.)\b", text, re.I):
            figure_like.append(index)

    pages_to_render = figure_like[:max_render_pages] or list(range(min(max_render_pages, len(doc))))
    for index in pages_to_render:
        page = doc[index]
        pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), alpha=False)
        image_path = image_dir / f"page_{index + 1:03d}.png"
        pix.save(image_path)
        rendered.append(str(image_path.relative_to(out_dir)))

    text_path = text_dir / "full_text.txt"
    text_path.write_text("".join(all_text), encoding="utf-8")
    return {
        "page_count": len(doc),
        "text_path": str(text_path.relative_to(out_dir)),
        "rendered_pages": rendered,
        "figure_like_pages": [p + 1 for p in figure_like],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", help="arXiv identifier, e.g. 2401.00001")
    parser.add_argument("--pdf-url", help="Direct official PDF URL")
    parser.add_argument("--label", help="Stable output directory label. Defaults to arXiv ID or PDF filename.")
    parser.add_argument("--out", default="papers", help="Output directory")
    parser.add_argument("--max-render-pages", type=int, default=8)
    parser.add_argument(
        "--skip-ocr",
        action="store_true",
        help="Compatibility flag; local OCR has been removed. Use execute_mineru.py for OCR/layout parsing.",
    )
    args = parser.parse_args()

    if not args.paper and not args.pdf_url:
        raise SystemExit("Provide --paper or --pdf-url")

    label = safe_name(args.label or args.paper or Path(urlparse(args.pdf_url).path).stem)
    out_dir = Path(args.out) / label
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {"label": label, "source_priority": []}

    pdf_path = out_dir / "paper.pdf"
    if args.paper:
        source_url, pdf_url = arxiv_urls(args.paper)
        source_archive = out_dir / "source.tar"
        try:
            download(source_url, source_archive)
            tex_files = extract_source(source_archive, out_dir)
            if tex_files:
                manifest["source_priority"].append("latex_source")
                manifest["tex_files"] = tex_files
        except Exception as exc:
            manifest["source_error"] = str(exc)
        if not pdf_path.exists():
            download(pdf_url, pdf_path)
    else:
        acquire_pdf(args.pdf_url, pdf_path)

    manifest["source_priority"].append("official_pdf")
    manifest["pdf"] = str(pdf_path.relative_to(out_dir))
    pdf_info = extract_pdf(pdf_path, out_dir, args.max_render_pages)
    manifest["pdf_parse"] = pdf_info

    manifest["ocr"] = {
        "engine": "mineru",
        "status": "not_run_by_acquire_parse",
        "next_step": "python3 execute_mineru.py --paper-dir <paper_dir> --is-ocr --enable-formula --enable-table",
    }

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(manifest_path)


if __name__ == "__main__":
    main()
