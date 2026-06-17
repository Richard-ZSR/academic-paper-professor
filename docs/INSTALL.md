# Installation Guide

## System Requirements

- macOS or Linux
- Python 3.10+
- Claude Code CLI or Codex CLI (latest versions recommended)

## Python Dependencies

The skill requires these Python packages:

```
requests>=2.31
PyMuPDF>=1.24
```

They are installed automatically when you run the installer, or manually:

```bash
python3 -m pip install -r requirements.txt
```

## Installation Methods

### Method 1: Install Script (Recommended)

Clone and run the installer:

```bash
git clone https://github.com/Richard-ZSR/academic-paper-professor.git
cd academic-paper-professor
./install.sh
```

This installs the skill for both Claude Code and Codex CLI.

### Method 2: Claude Code Plugin

From within a Claude Code session:

```text
/plugin marketplace add Richard-ZSR/academic-paper-professor
/plugin install academic-paper-professor
```

### Method 3: Manual Installation

**For Claude Code:**

```bash
mkdir -p ~/.claude/skills/academic-paper-professor
cp -R skills/academic-paper-professor/* ~/.claude/skills/academic-paper-professor/
python3 -m pip install -r ~/.claude/skills/academic-paper-professor/requirements.txt
```

**For Codex CLI:**

```bash
mkdir -p ~/.codex/skills/academic-paper-professor
cp -R codex/skills/academic-paper-professor/* ~/.codex/skills/academic-paper-professor/
python3 -m pip install -r ~/.codex/skills/academic-paper-professor/requirements.txt
```

## Verification

### Claude Code

Restart Claude Code. The skill auto-discovers from `~/.claude/skills/`. Try:

```
"Help me deep read a paper on transformer architectures"
```

### Codex CLI

Restart Codex CLI. Check with:

```
/skills
```

You should see `academic-paper-professor` in the list.

## MinerU Integration (Optional)

For enhanced PDF parsing with layout analysis, formula extraction, and table recognition:

1. Get a MinerU API token from [mineru.net](https://mineru.net)
2. Set the environment variable:

```bash
export MINERU_TOKEN='your-token-here'
```

Or pass it directly when running the script:

```bash
python3 "$SKILL_DIR/scripts/execute_mineru.py" --token your-token --paper-dir ./papers/2401.00001 --is-ocr --enable-formula --enable-table
```

## Troubleshooting

### Skill not triggering

- Ensure the skill directory exists at the correct path
- Restart your agent after installation
- Try an explicit academic paper request rather than a vague query

### Python dependency errors

```bash
python3 -m pip install --upgrade requests PyMuPDF
```

### MinerU token issues

If you don't have a MinerU token, the skill still works — it uses PyMuPDF for basic text extraction instead of MinerU's enhanced parsing.

## Uninstall

```bash
./install.sh --uninstall
```

Or manually:

```bash
rm -rf ~/.claude/skills/academic-paper-professor
rm -rf ~/.codex/skills/academic-paper-professor
```
