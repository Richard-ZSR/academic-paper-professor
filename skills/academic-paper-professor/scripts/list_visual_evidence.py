#!/usr/bin/env python3
"""List existing visual evidence for a paper without embedding image bytes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def find_images(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def iter_json_files(paper_dir: Path) -> Iterable[Path]:
    mineru_result = paper_dir / "mineru" / "result"
    if mineru_result.exists():
        yield from sorted(mineru_result.glob("*.json"))


def walk_json(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def load_visual_refs(paper_dir: Path) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    keys = {
        "img_path",
        "image_path",
        "image",
        "table_img_path",
        "table_image_path",
        "figure_path",
    }
    for json_file in iter_json_files(paper_dir):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for obj in walk_json(data):
            for key in keys:
                raw = obj.get(key)
                if isinstance(raw, str) and raw:
                    refs.append((str(json_file.relative_to(paper_dir)), raw))
    return refs


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List paper visual artifacts as paths, without embedding images."
    )
    parser.add_argument("--paper-dir", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument(
        "--absolute",
        action="store_true",
        help="Print absolute paths instead of paths relative to paper-dir.",
    )
    args = parser.parse_args()

    paper_dir = args.paper_dir.expanduser().resolve()
    if not paper_dir.exists():
        raise SystemExit(f"paper-dir does not exist: {paper_dir}")

    pdf = paper_dir / "paper.pdf"
    rendered = find_images(paper_dir / "rendered_pages")
    mineru_images = find_images(paper_dir / "mineru" / "result" / "images")
    other_images = [
        path
        for path in find_images(paper_dir)
        if path not in set(rendered) and path not in set(mineru_images)
    ]
    refs = load_visual_refs(paper_dir)

    def show_path(path: Path) -> str:
        return str(path) if args.absolute else rel(path, paper_dir)

    print(f"# Visual evidence index: {paper_dir.name}")
    print()
    print("Do not embed these images by default. Reference paths only when needed.")
    print()
    print("## PDF")
    print(f"- {show_path(pdf)}" if pdf.exists() else "- paper.pdf missing")
    print()
    print(f"## Rendered pages ({len(rendered)})")
    for path in rendered[: args.limit]:
        print(f"- {show_path(path)}")
    if len(rendered) > args.limit:
        print(f"- ... {len(rendered) - args.limit} more")
    print()
    print(f"## MinerU images ({len(mineru_images)})")
    for path in mineru_images[: args.limit]:
        print(f"- {show_path(path)}")
    if len(mineru_images) > args.limit:
        print(f"- ... {len(mineru_images) - args.limit} more")
    print()
    print(f"## Other images ({len(other_images)})")
    for path in other_images[: args.limit]:
        print(f"- {show_path(path)}")
    if len(other_images) > args.limit:
        print(f"- ... {len(other_images) - args.limit} more")
    print()
    print(f"## JSON visual references ({len(refs)})")
    for source, value in refs[: args.limit]:
        print(f"- {source}: {value}")
    if len(refs) > args.limit:
        print(f"- ... {len(refs) - args.limit} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
