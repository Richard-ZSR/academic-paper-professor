# academic-paper-professor

A cross-agent academic paper deep-reading skill that works with **Claude Code** and **Codex CLI**.

Act as a senior academic research professor for paper discovery, indexed acquisition, arXiv/PDF/source/MinerU parsing, single-paper deep reading, batch hot-paper analysis, experiment-by-experiment critique, theory reconstruction, historical roadmap tracing, and Markdown academic archiving.

## Quick Install

### One-Click Install (Both Agents)

```bash
git clone https://github.com/Richard-ZSR/academic-paper-professor.git
cd academic-paper-professor
./install.sh
```

### Claude Code Only

```bash
./install.sh --claude
```

### Codex CLI Only

```bash
./install.sh --codex
```

### Uninstall

```bash
./install.sh --uninstall
```

### Plugin Install (Claude Code)

If you use Claude Code plugin system:

```text
/plugin marketplace add Richard-ZSR/academic-paper-professor
/plugin install academic-paper-professor
```

## Prerequisites

- **Claude Code** or **Codex CLI** (latest version)
- `python3` (3.10+)
- Python packages: `requests>=2.31`, `PyMuPDF>=1.24` (install automatically via the install script)
- Optional: MinerU API token for PDF layout/OCR/formula/table parsing

## What It Does

| Mode | Description |
|------|-------------|
| **Discovery** | Search and select papers on a topic by time range |
| **Single-paper acquisition** | Download and parse one paper by arXiv ID, PDF URL, or title |
| **Single-paper deep reading** | Full professor-level deep analysis of one paper |
| **Batch hot-paper analysis** | Multi-paper deep reading with per-paper subagents |
| **Comparison** | Cross-paper synthesis report (on explicit request) |
| **Deep follow-up** | Interactive Q&A on an existing analysis |

## Skill Architecture

```
academic-paper-professor/
├── .claude-plugin/
│   └── plugin.json            # Claude Code plugin manifest
├── skills/
│   └── academic-paper-professor/
│       ├── SKILL.md           # Claude Code skill instructions
│       ├── requirements.txt   # Python dependencies
│       └── scripts/
│           ├── acquire_papers.py
│           ├── acquire_selected_papers.py
│           ├── validate_batch_ids.py
│           ├── execute_mineru.py
│           ├── generate_markdown_backbone.py
│           ├── list_visual_evidence.py
│           └── paper_acquire_parse.py
├── codex/
│   └── skills/
│       └── academic-paper-professor/
│           ├── SKILL.md           # Codex-adapted skill instructions
│           ├── manifest.json      # Codex skill manifest
│           ├── requirements.txt
│           ├── agents/
│           │   └── openai.yaml    # Codex agent interface config
│           └── scripts/
│               └── (same scripts)
├── docs/
│   └── INSTALL.md
├── install.sh                # Cross-agent installer
├── LICENSE
└── README.md
```

## Key Differences Between Claude and Codex Versions

| Feature | Claude Code | Codex CLI |
|---------|-------------|-----------|
| SKILL_DIR resolution | `$HOME/.claude/skills/academic-paper-professor` | `${CODEX_HOME:-$HOME/.codex}/skills/academic-paper-professor` |
| Subagent model scheduling | Full model for all stages | Downgraded model for Stage 2 acquisition/parsing |
| `User_Model`/`User_Thinking` params | Not in intent parsing | Added to intent parsing for runtime-aware scheduling |
| Agent interface file | N/A (native Claude subagents) | `agents/openai.yaml` for Codex agent routing |

## Usage Examples

### Single Paper Deep Reading

```
"Deep read the paper arXiv:2401.00001"
"Read this paper: https://arxiv.org/pdf/2401.00001"
```

### Batch Hot-Paper Analysis

```
"Find and analyze the top 5 papers on diffusion models from the last 2 weeks"
```

### Follow-up Questions

```
"Explain the training objective in more detail"
"What are the limitations of their evaluation?"
```

## License

MIT License — see [LICENSE](LICENSE).
