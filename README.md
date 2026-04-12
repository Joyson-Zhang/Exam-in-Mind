# Exam-in-Mind

> 面向考试科目的学习智能体 —— 自动构建分层知识树，输出为可离线浏览的 MkDocs 静态站 + 单文件 Markdown。

## 特性

- **一键生成**: 输入考试名称，自动联网查询考纲、构建三级知识树、生成详细讲解
- **联网搜索**: 通过 Brave Search API 查询最新官方考纲，确保知识点完整覆盖
- **分层知识树**: 章 (Unit) → 节 (Section) → 知识点 (Knowledge Point)，层次清晰
- **双格式输出**: MkDocs 静态站（带侧边栏导航和搜索）+ 单文件 Markdown（适合 Obsidian/Notion）
- **LaTeX 公式**: 所有数学公式使用 KaTeX 渲染，支持行内和行间公式
- **断点续跑**: 任意步骤中断后重启可从断点继续，不浪费已有 API 调用
- **多语言**: 支持中文 / 英文输出（通过 `--lang` 参数）

## 安装

### 1. 克隆项目

```bash
git clone <repo-url>
cd exam-in-mind
```

### 2. 创建虚拟环境

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -e ".[dev]"
```

### 4. 配置 API Key

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Key：

```
ANTHROPIC_API_KEY=sk-ant-xxxxx
BRAVE_SEARCH_API_KEY=BSAxxxxx
```

- **Anthropic API Key**: 必须。从 [console.anthropic.com](https://console.anthropic.com/) 获取
- **Brave Search API Key**: 推荐。从 [brave.com/search/api](https://brave.com/search/api/) 获取免费额度。不配置时程序仍可运行，但会跳过联网搜索

## 使用示例

### 基本用法

```bash
python -m exam_in_mind --exam "AP Calculus BC"
```

### 完整参数

```bash
python -m exam_in_mind \
  --exam "AP Calculus BC" \
  --lang zh \
  --model claude-sonnet-4-5 \
  --no-search \
  --restart \
  --output-dir ./output \
  --verbose
```

### 参数说明

| 参数 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `--exam` | 是 | - | 考试名称，如 `"AP Calculus BC"`、`"SAT Math"` |
| `--lang` | 否 | `zh` | 输出语言（`zh` 中文 / `en` 英文） |
| `--model` | 否 | 配置文件 | 覆盖 `config.yaml` 中的模型名称 |
| `--no-search` | 否 | `false` | 禁用 Brave Search，仅使用模型内置知识 |
| `--restart` | 否 | `false` | 忽略已有缓存，从头开始生成 |
| `--output-dir` | 否 | `./output` | 自定义输出目录 |
| `--verbose` | 否 | `false` | 打印详细日志和配置信息 |

### 查看结果

运行完成后，双击打开生成的站点首页：

```
output/ap_calculus_bc/site/index.html
```

或用 VS Code / Obsidian 打开单文件 Markdown：

```
output/ap_calculus_bc/full.md
```

## 配置说明

运行时配置在 `config.yaml` 中，关键字段：

```yaml
llm:
  model: "claude-sonnet-4-5"   # AI 模型，测试时可改为 claude-haiku-4-5
  max_tokens: 4096              # 单次 API 调用最大 token 数
  temperature: 0.3              # 低温度适合知识类生成

search:
  enabled: true                 # 是否启用联网搜索（也可用 --no-search 覆盖）

tree:
  level_1_count_hint: "8-12"   # 一级 Unit 数量提示（传入 prompt，非硬限制）
  level_2_count_hint: "4-8"    # 二级 Section 数量提示
  level_3_count_hint: "3-6"    # 三级知识点数量提示

output:
  base_dir: "./output"          # 输出根目录
  language: "zh"                # 默认输出语言
```

## 项目结构

```
exam-in-mind/
├── SPEC.md                    # 项目技术规格（架构、数据结构、流程定义）
├── PLAN.md                    # 8 阶段实施计划与验收标准
├── CLAUDE.md                  # Claude Code 行为准则
├── README.md                  # 本文件
├── .env.example               # API Key 模板
├── config.yaml                # 运行时配置
├── pyproject.toml             # 依赖管理
│
├── exam_in_mind/              # 主代码包
│   ├── main.py                # 命令行入口，串联全流程
│   ├── config.py              # 配置加载（.env + config.yaml）
│   ├── models.py              # Pydantic 数据模型（KnowledgeNode / LeafContent / ExamTree）
│   ├── llm_client.py          # Anthropic API 封装（含 tool use 循环）
│   ├── brave_search.py        # Brave Search API 封装
│   ├── tools.py               # Claude 自定义工具定义
│   ├── cache.py               # JSON 缓存读写 + 断点续跑
│   ├── prompts.py             # 所有 prompt 模板
│   ├── builders/
│   │   ├── outline_builder.py # 宏观框架构建器（联网查考纲 → 一级 Unit）
│   │   ├── tree_builder.py    # 递归分解器（Unit → Section → 知识点）
│   │   └── content_builder.py # 叶子内容生成器（定义 + 公式 + 易错点）
│   └── renderers/
│       ├── markdown_renderer.py  # 单文件 Markdown 输出
│       └── mkdocs_renderer.py    # MkDocs 站点输出
│
├── tests/                     # 单元测试
├── devlog/                    # 开发日志（每个 Phase 的复盘记录）
└── output/                    # 生成结果（.gitignore 排除）
```

## 产出物说明

每次运行后，`output/{exam_slug}/` 下包含：

| 文件/目录 | 说明 |
|---|---|
| `site/` | MkDocs 编译产物，双击 `index.html` 即可离线浏览 |
| `full.md` | 单文件 Markdown，可导入 Obsidian / Notion / VS Code |
| `tree.json` | 知识树原始 JSON 数据，支持手动编辑后重新渲染 |
| `docs/` | MkDocs 源 Markdown 文件 |
| `mkdocs.yml` | MkDocs 配置文件 |

## 常见问题

### Q: 提示 "ANTHROPIC_API_KEY 未设置"

确认 `.env` 文件存在于项目根目录，且包含有效的 API Key。注意不要有多余空格：

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Q: Brave Search 报 429 / 配额用尽

Brave Search 免费套餐有每月调用限制。两种解决方案：

1. 等待下个月配额重置
2. 使用 `--no-search` 参数跳过联网搜索，程序会使用模型内置知识生成大纲

### Q: 如何清理缓存重新生成？

```bash
# 方式一：使用 --restart 参数（自动备份旧缓存）
python -m exam_in_mind --exam "AP Calculus BC" --restart

# 方式二：手动删除 output 目录
rm -rf output/ap_calculus_bc/
```

### Q: 生成中断了怎么办？

直接重新运行相同命令，程序会检测到已有缓存并提示"是否继续上次进度"，选择 `Y` 即可从断点继续。

### Q: 如何切换模型？

编辑 `config.yaml` 中的 `llm.model` 字段，或使用命令行参数覆盖：

```bash
python -m exam_in_mind --exam "SAT Math" --model claude-haiku-4-5-20251001
```

## 项目文档

| 文件 | 用途 |
|---|---|
| `SPEC.md` | 项目技术规格书，定义架构、数据结构、流程、边界 |
| `PLAN.md` | 8 阶段实施计划，每个 Phase 的目标、交付物和验收标准 |
| `CLAUDE.md` | Claude Code 行为准则，确保 AI 辅助开发时遵守项目规则 |
| `devlog/` | 开发日志，记录每个 Phase 的决策过程和踩坑经验 |

## 关于本项目

Exam-in-Mind 使用 [Claude Code](https://claude.ai/code) 辅助开发，全程遵循 SPEC.md 规格书和 PLAN.md 分阶段计划，由Joyson Zhang担任产品经理与验收官、AI 负责编码实现。开发过程记录在 `devlog/` 目录中。
