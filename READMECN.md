# academic-paper-professor

跨 agent 学术论文深度研读技能，支持 **Claude Code** 和 **Codex CLI**。

以资深学术研究教授的角色，提供论文发现、索引化获取、arXiv/PDF/源码/MinerU 解析、单篇深度研读、批量热点论文分析、逐实验批判、理论重构、历史脉络追溯，以及 Markdown 学术归档。

[English Documentation](README.md)

---

## 提示词示例

以下两段标准提示词分别触发技能的两个核心工作流。在提示词中预先写明输出语言（中文或英文），即可让工作流免去二次确认直接执行。

### 单篇论文研读

通过 arXiv ID、PDF URL 或标题指向一篇论文：

```text
以研究教授的身份，对 arXiv:1706.03762 做一次完整的深度研读。获取源码并用 MinerU
解析，重构完整理论，逐个实验进行批判，追溯历史脉络，并用中文撰写分析报告。
```

### 热点论文 Top-N 下载与研读

给出主题、时间范围以及需要筛选的论文数量：

```text
找出最近一个月关于「大语言模型 Agent」最热门的 10 篇论文，校验、下载并解析全部论文，
然后为每一篇分别撰写教授级的深度研读报告，使用中文输出。
```

---

## 技能安装目录

技能安装后，文件会被复制到对应 agent 的 skills 目录中，agent 启动时自动发现并加载。

### Claude Code

Claude Code 的用户级 skill 目录为：

```
~/.claude/skills/<skill-name>/
```

本技能安装路径：

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

本技能安装路径：

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
| **Plugin 缓存** | `~/.claude/plugins/cache/<marketplace>/<plugin>/<ver>/skills/` | 无（Codex 无 plugin 系统） |
| **支持 Symlink** | ✅ 是 | ✅ 是 |
| **支持直接复制** | ✅ 是 | ✅ 是 |

---

## 快速安装

### 一键安装（两个 Agent 同时安装）

```bash
git clone https://github.com/Richard-ZSR/academic-paper-professor.git
cd academic-paper-professor
./install.sh
```

### 仅安装 Claude Code

```bash
./install.sh --claude
```

### 仅安装 Codex CLI

```bash
./install.sh --codex
```

### 卸载

```bash
./install.sh --uninstall
```

### Plugin 方式安装（Claude Code）

如果你使用 Claude Code 的 plugin 系统（v3.7.0+）：

```text
/plugin marketplace add Richard-ZSR/academic-paper-professor
/plugin install academic-paper-professor
```

Plugin 安装方式会将 skill 放入 `~/.claude/plugins/cache/` 而非 `~/.claude/skills/`，两者均能被 Claude Code 自动发现。

### 手动安装

手动安装即复制 skill 文件到对应目录：

**Claude Code：**

```bash
mkdir -p ~/.claude/skills/academic-paper-professor/scripts
cp skills/academic-paper-professor/SKILL.md ~/.claude/skills/academic-paper-professor/
cp skills/academic-paper-professor/requirements.txt ~/.claude/skills/academic-paper-professor/
cp skills/academic-paper-professor/scripts/*.py ~/.claude/skills/academic-paper-professor/scripts/
python3 -m pip install -r ~/.claude/skills/academic-paper-professor/requirements.txt
```

**Codex CLI：**

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

## 前置条件

- **Claude Code** 或 **Codex CLI**（最新版本）
- `python3`（3.10+）
- Python 包：`requests>=2.31`、`PyMuPDF>=1.24`
- 可选：[MinerU](https://mineru.net) API 令牌，用于增强版 PDF 版面分析/OCR/公式/表格解析

安装 Python 依赖：

```bash
python3 -m pip install -r requirements.txt
```

---

## MinerU 令牌配置

MinerU 提供云端 PDF 版面分析、OCR、公式提取和表格解析。增强解析需要免费的 API 令牌。技能在没有 MinerU 的情况下也能工作（使用 PyMuPDF + LaTeX 源码），但配合 MinerU 能产出更优的分析。

### 如何获取令牌

1. **注册**：访问 https://mineru.net 注册免费账号（邮箱或手机号）。
2. **获取 API 令牌**：登录后进入 **个人中心 → API 密钥** 创建或复制你的令牌。
3. **配置** — 选择以下任一方式：

   **方式 A（推荐）**：设置环境变量：
   ```bash
   # 添加到 ~/.bashrc、~/.zshrc 或 shell 配置文件
   export MINERU_TOKEN='在此粘贴你的令牌'
   ```

   **方式 B**：通过命令行参数传入：
   ```bash
   python3 "$SKILL_DIR/scripts/execute_mineru.py" --token '在此粘贴你的令牌' \
     --paper-dir ./papers/2401.00001 --is-ocr --enable-formula --enable-table
   ```

   **方式 C**：编辑脚本中的回退常量（公共机器不推荐）：
   ```bash
   # 打开 scripts/execute_mineru.py，找到 LOCAL_MINERU_TOKEN，粘贴你的令牌
   LOCAL_MINERU_TOKEN = "your-token-here"
   ```

**免费额度**：MinerU 提供免费额度，每日 API 调用次数有限，详见 https://mineru.net。

**安全提醒**：请勿分享、提交或暴露你的 API 令牌。技能不会在报告或对话中打印令牌值。

---

## 功能概览

| 模式 | 说明 |
|------|------|
| **发现** | 按时间范围搜索和筛选论文 |
| **单篇获取** | 通过 arXiv ID、PDF URL 或标题下载并解析一篇论文 |
| **单篇深度研读** | 对一篇论文进行教授级深度分析 |
| **批量热点分析** | 多论文深度研读，每篇论文独立子 agent |
| **比较** | 跨论文综合报告（仅按用户明确请求生成） |
| **深度追问** | 对已有分析的交互式问答 |

---

## 技能架构

```
academic-paper-professor/            ← 本仓库
├── .claude-plugin/
│   └── plugin.json                  # Claude Code plugin 清单（用于 /plugin install）
├── skills/
│   └── academic-paper-professor/   ← Claude Code skill 源（→ 复制到 ~/.claude/skills/）
│       ├── SKILL.md                 # Claude Code 技能指令
│       ├── requirements.txt         # Python 依赖
│       └── scripts/                 # 7 个辅助 Python 脚本
├── codex/
│   └── skills/
│       └── academic-paper-professor/ ← Codex CLI skill 源（→ 复制到 ~/.codex/skills/）
│           ├── SKILL.md              # Codex 适配版技能指令
│           ├── manifest.json         # Codex 打包清单
│           ├── requirements.txt
│           ├── agents/
│           │   └── openai.yaml       # Codex agent 界面声明
│           └── scripts/              # 7 个辅助 Python 脚本
├── docs/
│   └── INSTALL.md                   # 详细安装指南
├── install.sh                       # 跨 agent 安装/卸载脚本
├── LICENSE
└── README.md
```

**安装流程**：`install.sh` 将 `skills/academic-paper-professor/` 下的文件复制到 `~/.claude/skills/academic-paper-professor/`，将 `codex/skills/academic-paper-professor/` 下的文件复制到 `~/.codex/skills/academic-paper-professor/`。Agent 启动时自动从对应的 skills 目录发现并加载技能。

---

## Claude 版与 Codex 版差异

| 特性 | Claude Code (`skills/`) | Codex CLI (`codex/skills/`) |
|------|------------------------|-----------------------------|
| **SKILL_DIR 解析** | `$HOME/.claude/skills/academic-paper-professor` | `${CODEX_HOME:-$HOME/.codex}/skills/academic-paper-professor` |
| **Stage 2 模型调度** | 全量模型用于所有阶段 | 获取/解析子 agent 降级模型 + medium thinking |
| **Intent 解析参数** | 无 `User_Model`/`User_Thinking` | 添加运行时感知调度参数 |
| **Agent 接口文件** | 无（原生 Claude subagent） | `agents/openai.yaml` 声明 agent 界面 |

---

## 使用示例

### 单篇深度研读

```
"深度研读论文 arXiv:2401.00001"
"Read this paper: https://arxiv.org/pdf/2401.00001"
```

### 批量热点分析

```
"找出并分析过去两周关于扩散模型的热门论文 top 5"
```

### 深度追问

```
"详细解释他们的训练目标"
"他们的评估方法有什么局限性？"
```

---

## 验证

### Claude Code

重启 Claude Code。技能自动从 `~/.claude/skills/academic-paper-professor/SKILL.md` 加载。测试：

```
"帮我深度研读一篇关于 transformer 架构的论文"
```

### Codex CLI

重启 Codex CLI。检查已安装技能：

```
/skills
```

列表中应出现 `academic-paper-professor`。

---

## 许可证

MIT License — 详见 [LICENSE](LICENSE)。
