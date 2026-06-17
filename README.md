# academic-paper-professor

A cross-agent academic paper deep-reading skill that works with **Claude Code** and **Codex CLI**.

Act as a senior academic research professor for paper discovery, indexed acquisition, arXiv/PDF/source/MinerU parsing, single-paper deep reading, batch hot-paper analysis, experiment-by-experiment critique, theory reconstruction, historical roadmap tracing, and Markdown academic archiving.

---

## Skill Installation Directories

技能安装后，文件会被复制到对应 agent 的 skills 目录中，agent 启动时自动发现并加载。

### Claude Code

Claude Code 的用户级 skill 目录为：

```
~/.claude/skills/<skill-name>/
```

本 skill 安装路径：

```
~/.claude/skills/academic-paper-professor/
├── SKILL.md                  # 技能指令（agent 自动加载）
├── requirements.txt          # Python 依赖
└── scripts/                  # 辅助脚本（SKILL.md 中引用）
    ├── acquire_papers.py
    ├── acquire_selected_papers.py
    ├── validate_batch_ids.py
    ├── execute_mineru.py
    ├── generate_markdown_backbone.py
    ├── list_visual_evidence.py
    └── paper_acquire_parse.py
```

**发现机制**：Claude Code 启动时扫描 `~/.claude/skills/` 下所有子目录，读取每个子目录中的 `SKILL.md` frontmatter（`name` + `description`）作为技能元数据，加载到 `available_skills` 列表。目录名即为技能 ID，`SKILL.md` 中引用的脚本路径基于该目录解析。

**Symlink 支持**：`~/.claude/skills/<skill-name>` 可以是符号链接，指向实际文件位置（如 `~/.cc-switch/skills/<skill-name>`）。Claude Code 会自动解析 symlink 后读取内容。

**Plugin 安装路径**（另一种安装方式）：通过 `/plugin install` 安装的技能存放在：

```
~/.claude/plugins/cache/<marketplace>/<plugin-name>/<version>/skills/<skill-name>/
```

Plugin 系统额外维护 `~/.claude/plugins/installed_plugins.json` 作为注册表。

### Codex CLI

Codex CLI 的用户级 skill 目录为：

```
~/.codex/skills/<skill-name>/
```

本 skill 安装路径：

```
~/.codex/skills/academic-paper-professor/
├── SKILL.md                  # 技能指令（agent 自动加载）
├── manifest.json             # Codex 打包清单
├── requirements.txt          # Python 依赖
├── agents/
│   └── openai.yaml          # Codex agent 界面配置
└── scripts/                  # 辅助脚本（SKILL.md 中引用）
    ├── acquire_papers.py
    ├── acquire_selected_papers.py
    ├── validate_batch_ids.py
    ├── execute_mineru.py
    ├── generate_markdown_backbone.py
    ├── list_visual_evidence.py
    └── paper_acquire_parse.py
```

**发现机制**：Codex CLI 启动时扫描 `~/.codex/skills/` 下所有子目录，读取每个子目录中的 `SKILL.md` frontmatter。与 Claude Code 类似，但 Codex 额外支持 `agents/openai.yaml` 声明 agent 界面元数据（display_name、short_description、default_prompt），以及 `manifest.json` 记录打包来源信息。

**Symlink 支持**：与 Claude Code 相同，`~/.codex/skills/<skill-name>` 也可以是符号链接。

### 目录对照表

| 项目 | Claude Code | Codex CLI |
|------|-------------|-----------|
| **Skill 根目录** | `~/.claude/skills/` | `~/.codex/skills/` |
| **Skill 安装路径** | `~/.claude/skills/academic-paper-professor/` | `~/.codex/skills/academic-paper-professor/` |
| **SKILL.md 中的 SKILL_DIR** | `$HOME/.claude/skills/academic-paper-professor` | `${CODEX_HOME:-$HOME/.codex}/skills/academic-paper-professor` |
| **Skill 发现文件** | `SKILL.md` (frontmatter) | `SKILL.md` (frontmatter) + `agents/openai.yaml` |
| **打包清单** | `.claude-plugin/plugin.json`（仓库级） | `manifest.json`（skill 级） |
| **Plugin 缓存** | `~/.claude/plugins/cache/<marketplace>/<plugin>/<ver>/skills/` | N/A（Codex 无 plugin 系统） |
| **支持 Symlink** | ✅ 是 | ✅ 是 |
| **支持直接复制** | ✅ 是 | ✅ 是 |

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

如果你使用 Claude Code 的 plugin 系统（v3.7.0+）：

```text
/plugin marketplace add Richard-ZSR/academic-paper-professor
/plugin install academic-paper-professor
```

Plugin 安装方式会将 skill 放入 `~/.claude/plugins/cache/` 而非 `~/.claude/skills/`，两者均能被 Claude Code 自动发现。

### Manual Install

手动安装即复制 skill 文件到对应目录：

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

安装 Python 依赖：

```bash
python3 -m pip install -r requirements.txt
```

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
academic-paper-professor/          ← 本仓库
├── .claude-plugin/
│   └── plugin.json                # Claude Code plugin 清单（用于 /plugin install）
├── skills/
│   └── academic-paper-professor/ ← Claude Code skill 源（→ 复制到 ~/.claude/skills/）
│       ├── SKILL.md               # Claude Code 技能指令
│       ├── requirements.txt       # Python 依赖
│       └── scripts/               # 7 个辅助 Python 脚本
├── codex/
│   └── skills/
│       └── academic-paper-professor/ ← Codex CLI skill 源（→ 复制到 ~/.codex/skills/）
│           ├── SKILL.md            # Codex 适配版技能指令
│           ├── manifest.json       # Codex 打包清单
│           ├── requirements.txt
│           ├── agents/
│           │   └── openai.yaml     # Codex agent 界面声明
│           └── scripts/            # 7 个辅助 Python 脚本
├── docs/
│   └── INSTALL.md                 # 详细安装指南
├── install.sh                     # 跨 agent 安装/卸载脚本
├── LICENSE
└── README.md
```

**安装流程**：`install.sh` 将 `skills/academic-paper-professor/` 下的文件复制到 `~/.claude/skills/academic-paper-professor/`，将 `codex/skills/academic-paper-professor/` 下的文件复制到 `~/.codex/skills/academic-paper-professor/`。Agent 启动时自动从对应的 skills 目录发现并加载技能。

---

## Key Differences Between Claude and Codex Versions

| Feature | Claude Code (`skills/`) | Codex CLI (`codex/skills/`) |
|---------|------------------------|-----------------------------|
| **SKILL_DIR 解析** | `$HOME/.claude/skills/academic-paper-professor` | `${CODEX_HOME:-$HOME/.codex}/skills/academic-paper-professor` |
| **Stage 2 模型调度** | 全量模型用于所有阶段 | 获取/解析子 agent 降级模型 + medium thinking |
| **Intent 解析参数** | 无 `User_Model`/`User_Thinking` | 添加运行时感知调度参数 |
| **Agent 接口文件** | 无（原生 Claude subagent） | `agents/openai.yaml` 声明 agent 界面 |

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

重启 Claude Code 后，技能自动从 `~/.claude/skills/academic-paper-professor/SKILL.md` 加载。测试：

```
"Help me deep read a paper on transformer architectures"
```

### Codex CLI

重启 Codex CLI 后，检查已安装技能：

```
/skills
```

列表中应出现 `academic-paper-professor`。

---

## License

MIT License — see [LICENSE](LICENSE).
