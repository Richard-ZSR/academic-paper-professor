#!/usr/bin/env bash
# install.sh — Install academic-paper-professor skill for Claude Code and/or Codex CLI
# Usage:
#   ./install.sh              # install both Claude + Codex
#   ./install.sh --claude     # install Claude Code skill only
#   ./install.sh --codex      # install Codex skill only
#   ./install.sh --uninstall  # remove both

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_SKILL_DIR="$HOME/.claude/skills/academic-paper-professor"
CODEX_SKILL_DIR="$HOME/.codex/skills/academic-paper-professor"

install_claude() {
    echo "Installing academic-paper-professor for Claude Code..."
    mkdir -p "$CLAUDE_SKILL_DIR"
    cp -R "$SCRIPT_DIR/skills/academic-paper-professor/"* "$CLAUDE_SKILL_DIR/"
    echo "  -> Installed to $CLAUDE_SKILL_DIR"
    echo "  -> Scripts: $(ls "$CLAUDE_SKILL_DIR/scripts/" | wc -l | tr -d ' ') files"
    echo "  -> SKILL.md: $(wc -l < "$CLAUDE_SKILL_DIR/SKILL.md") lines"
    echo ""
    echo "  Install Python dependencies:"
    echo "    python3 -m pip install -r \"$CLAUDE_SKILL_DIR/requirements.txt\""
    echo ""
    echo "  Verify: restart Claude Code and the skill will auto-discover."
}

install_codex() {
    echo "Installing academic-paper-professor for Codex CLI..."
    mkdir -p "$CODEX_SKILL_DIR"
    cp -R "$SCRIPT_DIR/codex/skills/academic-paper-professor/"* "$CODEX_SKILL_DIR/"
    echo "  -> Installed to $CODEX_SKILL_DIR"
    echo "  -> Scripts: $(ls "$CODEX_SKILL_DIR/scripts/" | wc -l | tr -d ' ') files"
    echo "  -> SKILL.md: $(wc -l < "$CODEX_SKILL_DIR/SKILL.md") lines"
    echo "  -> agents/openai.yaml: present ($(wc -l < "$CODEX_SKILL_DIR/agents/openai.yaml") lines)"
    echo ""
    echo "  Install Python dependencies:"
    echo "    python3 -m pip install -r \"$CODEX_SKILL_DIR/requirements.txt\""
    echo ""
    echo "  Verify: restart Codex CLI and type /skills to see academic-paper-professor."
}

uninstall() {
    echo "Uninstalling academic-paper-professor..."
    if [ -d "$CLAUDE_SKILL_DIR" ]; then
        rm -rf "$CLAUDE_SKILL_DIR"
        echo "  -> Removed Claude Code skill at $CLAUDE_SKILL_DIR"
    fi
    if [ -d "$CODEX_SKILL_DIR" ]; then
        rm -rf "$CODEX_SKILL_DIR"
        echo "  -> Removed Codex skill at $CODEX_SKILL_DIR"
    fi
    echo "Done."
}

case "${1:-}" in
    --claude)
        install_claude
        ;;
    --codex)
        install_codex
        ;;
    --uninstall)
        uninstall
        ;;
    "")
        install_claude
        install_codex
        echo "=============================="
        echo "Installation complete!"
        echo "Restart your agent (Claude Code / Codex) to activate the skill."
        ;;
    *)
        echo "Usage: $0 [--claude|--codex|--uninstall]"
        exit 1
        ;;
esac
