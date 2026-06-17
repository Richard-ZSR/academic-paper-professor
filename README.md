# academic-paper-professor

A cross-agent academic paper deep-reading skill for **Claude Code** and **Codex CLI**.

Act as a senior academic research professor for paper discovery, indexed acquisition, arXiv/PDF/source/MinerU parsing, single-paper deep reading, batch hot-paper analysis, experiment-by-experiment critique, theory reconstruction, historical roadmap tracing, and Markdown academic archiving.

[中文文档](READMECN.md)

---

## Skill Installation Directories

After installation, skill files are copied to the corresponding agent's skills directory. The agent auto-discovers and loads them on startup.

### Claude Code

The user-level skill directory for Claude Code is:

```
~/.claude/skills/<skill-name>/
```

This skill installs to:

```
~/.claude/skills/academic-paper-professor/
├── SKILL.md                  # Skill instructions (auto-loaded by agent)
├── requirements.txt          # Python dependencies
└── scripts/                  # Helper scripts (referenced in SKILL.md)
    ├── acquire_papers.py
    ├── acquire_selected_papers.py
    ├── validate_batch_ids.py
    ├── execute_mineru.py
    ├── generate_markdown_backbone.py
    ├── list_visual_evidence.py
    └── paper_acquire_parse.py
```

**Discovery mechanism**: On startup, Claude Code scans all subdirectories under `~/.claude/skills/`, reading each subdirectory's `SKILL.md` frontmatter (`name` + `description`) as skill metadata, loading it into the `available_skills` list. The directory name is the skill ID; script paths referenced in `SKILL.md` resolve relative to that directory.

**Symlink support**: `~/.claude/skills/<skill-name>` may be a symlink pointing to an actual file location (e.g. `~/.cc-switch/skills/<skill-name>`). Claude Code automatically resolves symlinks and reads the content.

**Plugin install path** (alternative method): Skills installed via `/plugin install` are stored at:

```
~/.claude/plugins/cache/<marketplace>/<plugin-name>/<version>/skills/<skill-name>/
```

The plugin system also maintains `~/.claude/plugins/installed_plugins.json` as a registry.

### Codex CLI

The user-level skill directory for Codex CLI is:

```
~/.codex/skills/<skill-name>/
```

This skill installs to:

```
~/.codex/skills/academic-paper-professor/
├── SKILL.md                  # Skill instructions (auto-loaded by agent)
├── manifest.json             # Codex packaging manifest
├── requirements.txt          # Python dependencies
├── agents/
│   └── openai.yaml          # Codex agent interface config
└── scripts/                  # Helper scripts (referenced in SKILL.md)
    ├── acquire_papers.py
    ├── acquire_selected_papers.py
    ├── validate_batch_ids.py
    ├── execute_mineru.py
    ├── generate_markdown_backbone.py
    ├── list_visual_evidence.py
    └── paper_acquire_parse.py
```

**Discovery mechanism**: On startup, Codex CLI scans all subdirectories under `~/.codex/skills/`, reading each subdirectory's `SKILL.md` frontmatter. Similar to Claude Code, but Codex additionally supports `agents/openai.yaml` for declaring agent interface metadata (display_name, short_description, default_prompt), and `manifest.json` for packaging origin information.

**Symlink support**: Same as Claude Code, `~/.codex/skills/<skill-name>` may also be a symlink.

### Directory Comparison

| Item | Claude Code | Codex CLI |
|------|-------------|-----------|
| **Skill root directory** | `~/.claude/skills/` | `~/.codex/skills/` |
| **Skill install path** | `~/.claude/skills/academic-paper-professor/` | `~/.codex/skills/academic-paper-professor/` |
| **SKILL_DIR in SKILL.md** | `$HOME/.claude/skills/academic-paper-professor` | `${CODEX_HOME:-$HOME/.codex}/skills/academic-paper-professor` |
| **Skill discovery file** | `SKILL.md` (frontmatter) | `SKILL.md` (frontmatter) + `agents/openai.yaml` |
| **Packaging manifest** | `.claude-plugin/plugin.json` (repo-level) | `manifest.json` (skill-level) |
| **Plugin cache** | `~/.claude/plugins/cache/<marketplace>/<plugin>/<ver>/skills/` | N/A (no plugin system) |
| **Supports symlinks** | Yes | Yes |
| **Supports direct copy** | Yes | Yes |

---

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

If you use the Claude Code plugin system (v3.7.0+):

```text
/plugin marketplace add Richard-ZSR/academic-paper-professor
/plugin install academic-paper-professor
```

Plugin installs place the skill into `~/.claude/plugins/cache/` instead of `~/.claude/skills/` — both are auto-discovered by Claude Code.

### Manual Install

Manual installation copies skill files to the corresponding directory:

**Claude Code:**

```bash
mkdir -p ~/.claude/skills/academic-paper-professor/scripts
cp skills/academic-paper-professor/SKILL.md ~/.claude/skills/academic-paper-professor/
cp skills/academic-paper-professor/requirements.txt ~/.claude/skills/academic-paper-professor/
cp skills/academic-paper-professor/scripts/*.py ~/.claude/skills/academic-paper-professor/scripts/
python3 -m pip install -r ~/.claude/skills/academic-paper-professor/requirements.txt
```

**Codex CLI:**

```bash
mkdir -p ~/.codex/skills/academic-paper-professor/scripts
mkdir -p ~/.codex/skills/academic-paper-professor/agents
cp codex/skills/academic-paper-professor/SKILL.md ~/.codex/skills/academic-paper-professor/
cp codex/skills/academic-paper-professor/manifest.json ~/.codex/skills/academic-paper-professor/
cp codex/skills/academic-paper-professor/requirements.txt ~/.codex/skills/academic-paper-professor/
cp codex/skills/academic-paper-professor/agents/openai.yaml ~/.codex/skills/academic-paper-professor/agents/
cp codex/skills/academic-paper-professor/scripts/*.py ~/.codex/skills/academic-paper-professor/scripts/
python3 -m pip install -r ~/.codex/skills/academic-paper-professor/requirements.txt
```

---

## Prerequisites

- **Claude Code** or **Codex CLI** (latest version)
- `python3` (3.10+)
- Python packages: `requests>=2.31`, `PyMuPDF>=1.24`
- Optional: [MinerU](https://mineru.net) API token for enhanced PDF layout/OCR/formula/table parsing

Install Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

---

## MinerU Token Setup

MinerU provides cloud-based PDF layout analysis, OCR, formula extraction, and table parsing. A free API token is required for enhanced parsing. The skill works without MinerU (using PyMuPDF + LaTeX source) but produces better analyses with it.

### How to Get Your Token

1. **Register**: Visit https://mineru.net and sign up for a free account (email or phone).
2. **Get API Token**: After logging in, go to **Dashboard → API Keys** to create or copy your token.
3. **Configure** — choose ONE method:

   **Method A (recommended)**: Set environment variable:
   ```bash
   # Add to ~/.bashrc, ~/.zshrc, or your shell profile
   export MINERU_TOKEN='paste-your-token-here'
   ```

   **Method B**: Pass via CLI flag:
   ```bash
   python3 "$SKILL_DIR/scripts/execute_mineru.py" --token 'paste-your-token-here' \
     --paper-dir ./papers/2401.00001 --is-ocr --enable-formula --enable-table
   ```

   **Method C**: Edit the fallback constant in the script (not recommended for shared machines):
   ```bash
   # Open scripts/execute_mineru.py, find LOCAL_MINERU_TOKEN, paste your token
   LOCAL_MINERU_TOKEN = "your-token-here"
   ```

**Free Tier**: MinerU provides a free tier with limited daily API calls. See https://mineru.net for current limits.

**Security**: Do not share, commit, or expose your API token. The skill never prints token values in reports or chat.

---

## What It Does

| Mode | Description |
|------|-------------|
| **Discovery** | Search and select papers on a topic by time range |
| **Single-paper acquisition** | Download and parse one paper by arXiv ID, PDF URL, or title |
| **Single-paper deep reading** | Full professor-level deep analysis of one paper |
| **Batch hot-paper analysis** | Multi-paper deep reading with per-paper subagents |
| **Comparison** | Cross-paper synthesis report (on explicit request) |
| **Deep follow-up** | Interactive Q&A on an existing analysis |

---

## Skill Architecture

```
academic-paper-professor/            ← This repository
├── .claude-plugin/
│   └── plugin.json                  # Claude Code plugin manifest (for /plugin install)
├── skills/
│   └── academic-paper-professor/   ← Claude Code skill source (→ copy to ~/.claude/skills/)
│       ├── SKILL.md                 # Claude Code skill instructions
│       ├── requirements.txt         # Python dependencies
│       └── scripts/                 # 7 helper Python scripts
├── codex/
│   └── skills/
│       └── academic-paper-professor/ ← Codex CLI skill source (→ copy to ~/.codex/skills/)
│           ├── SKILL.md              # Codex-adapted skill instructions
│           ├── manifest.json         # Codex packaging manifest
│           ├── requirements.txt
│           ├── agents/
│           │   └── openai.yaml       # Codex agent interface declaration
│           └── scripts/              # 7 helper Python scripts
├── docs/
│   └── INSTALL.md                   # Detailed installation guide
├── install.sh                       # Cross-agent install/uninstall script
├── LICENSE
└── README.md
```

**Install flow**: `install.sh` copies `skills/academic-paper-professor/` to `~/.claude/skills/academic-paper-professor/` and `codex/skills/academic-paper-professor/` to `~/.codex/skills/academic-paper-professor/`. Agents auto-discover skills from their respective skills directories on startup.

---

## Key Differences Between Claude and Codex Versions

| Feature | Claude Code (`skills/`) | Codex CLI (`codex/skills/`) |
|---------|------------------------|-----------------------------|
| **SKILL_DIR resolution** | `$HOME/.claude/skills/academic-paper-professor` | `${CODEX_HOME:-$HOME/.codex}/skills/academic-paper-professor` |
| **Stage 2 model scheduling** | Full model for all stages | Downgraded model + medium thinking for acquisition/parsing subagents |
| **Intent parsing params** | No `User_Model`/`User_Thinking` | Added for runtime-aware scheduling |
| **Agent interface file** | N/A (native Claude subagents) | `agents/openai.yaml` for Codex agent routing |

---

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

---

## Verification

### Claude Code

Restart Claude Code. The skill auto-loads from `~/.claude/skills/academic-paper-professor/SKILL.md`. Test with:

```
"Help me deep read a paper on transformer architectures"
```

### Codex CLI

Restart Codex CLI. Check installed skills:

```
/skills
```

You should see `academic-paper-professor` in the list.

---

## License

MIT License — see [LICENSE](LICENSE).
