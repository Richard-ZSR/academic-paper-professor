from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import acquire_papers


WORK_ROOT = Path.cwd()
DEFAULT_CONFIG = WORK_ROOT / "paper_batch_config.json"


BACKBONE_SECTIONS = [
    "Paper Card",
    "Evidence Inventory",
    "Abstract-Level Claim Extraction",
    "Research Problem and Formalization",
    "Complete Theory and Method Logic Flow",
    "Terminology, Methods, and Processes Requiring Explanation",
    "Key Figures and Tables",
    "Experiment-by-Experiment Analysis",
    "Cross-Experiment Synthesis",
    "What the Paper Proves",
    "What Remains Unproven",
    "Limitations and Failure Conditions",
    "Historical Research Roadmap",
    "Professor-Level Critical Judgment",
    "Archive Card",
    "Open Questions for Deep Reading",
]


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def output_name(config: dict, force_timestamp: bool) -> str:
    analysis = config.get("analysis") or {}
    if force_timestamp:
        return f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    return analysis.get("backbone_filename") or analysis.get("output_filename") or "analysis.md"


def title_for(paper: dict, label: str) -> str:
    return str(paper.get("title") or label).strip()


def evidence_paths(paper_dir: Path) -> list[str]:
    candidates = [
        paper_dir / "manifest.json",
        paper_dir / "paper.pdf",
        paper_dir / "text" / "full_text.txt",
        paper_dir / "mineru" / "mineru_manifest.json",
        paper_dir / "mineru" / "result" / "full.md",
        paper_dir / "source",
        paper_dir / "selection_metadata.json",
    ]
    return [str(path) for path in candidates if path.exists()]


def build_backbone(config: dict, paper: dict, paper_dir: Path) -> str:
    label = acquire_papers.paper_label(paper)
    title = title_for(paper, label)
    time_frame = config.get("time_frame") or {}
    paths = evidence_paths(paper_dir)
    path_lines = "\n".join(f"- `{path}`" for path in paths) or "- No parsed evidence files found yet."
    section_blocks = []
    for section in BACKBONE_SECTIONS:
        section_blocks.append(
            "\n".join(
                [
                    f"## {section}",
                    "",
                    "<!-- Fill this section from PDF text, LaTeX source, MinerU output, figures/tables, and verified external sources. Do not leave placeholders in the final analysis. -->",
                    "",
                ]
            )
        )

    return "\n".join(
        [
            f"# {title}",
            "",
            "<!-- Markdown backbone only. The model must fill every section with paper-specific analysis before this becomes a final report. -->",
            "",
            "## Backbone Metadata",
            "",
            f"- Local label: `{label}`",
            f"- Topic: {config.get('topic', paper.get('topic_fit', ''))}",
            f"- Time frame: {time_frame.get('start', '')} to {time_frame.get('end', '')}",
            f"- Rank: {paper.get('rank', '')}",
            f"- arXiv ID: {paper.get('arxiv_id') or paper.get('paper') or ''}",
            f"- DOI: {paper.get('doi', '')}",
            f"- PDF URL: {paper.get('pdf_url', '')}",
            "",
            "## Required Evidence Files",
            "",
            path_lines,
            "",
            *section_blocks,
        ]
    )


def write_index(config: dict, target_dir: Path, output_filename: str) -> None:
    rows = [
        "| Rank | ID | Title | Backbone |",
        "| --- | --- | --- | --- |",
    ]
    for paper in sorted(config.get("papers") or [], key=lambda item: item.get("rank", 10**9)):
        label = acquire_papers.paper_label(paper)
        title = title_for(paper, label).replace("|", "\\|")
        rows.append(f"| {paper.get('rank', '')} | {label} | {title} | `{target_dir / label / output_filename}` |")

    (target_dir / "INDEX.md").write_text(
        "\n".join(
            [
                f"# {config.get('batch_name', target_dir.name)}",
                "",
                "This index lists Markdown backbones. A backbone is not a completed analysis.",
                "",
                *rows,
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate required Markdown analysis backbones without filling paper content."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Batch JSON config path.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing backbone files.")
    parser.add_argument(
        "--timestamp",
        action="store_true",
        help="Write analysis_YYYYMMDD_HHMMSS.md, used for repeat parsing of one paper.",
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config_dir = config_path.parent
    config = load_config(config_path)
    target_dir = acquire_papers.resolve_path(config.get("target_dir"), config_dir)
    if target_dir is None:
        root = acquire_papers.resolve_path(config.get("root"), config_dir) or config_dir
        target_dir = root / str(config["batch_name"])
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = output_name(config, args.timestamp)
    wrote = 0
    skipped = 0
    for paper in config.get("papers") or []:
        label = acquire_papers.paper_label(paper)
        paper_dir = target_dir / label
        paper_dir.mkdir(parents=True, exist_ok=True)
        output_path = paper_dir / filename
        if output_path.exists() and not args.force and not args.timestamp:
            print(f"skip existing backbone: {output_path}")
            skipped += 1
            continue
        output_path.write_text(build_backbone(config, paper, paper_dir), encoding="utf-8")
        wrote += 1

    write_index(config, target_dir, filename)
    print(f"wrote {wrote} Markdown backbones; skipped {skipped}")
    print(target_dir / "INDEX.md")


if __name__ == "__main__":
    main()
