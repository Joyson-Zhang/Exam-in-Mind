# Exam-in-Mind 项目规格说明书 (SPEC)

> 本文件是项目的"宪法"。所有技术选型和架构决策已固定,实现时不得擅自更改。如需变更,必须先与用户确认。

## 1. 项目目标

构建一个命令行智能体,针对用户指定的考试科目,自动:
1. 联网查询官方考纲(若有)
2. 构建该科目的分层知识树(章 → 节 → 知识点)
3. 为每个叶子知识点生成详细讲解
4. 输出为可本地阅读的 MkDocs 静态站 + 单文件 Markdown

**首期测试科目**: AP Calculus BC

## 2. 技术栈(已固定,不得更改)

| 类别 | 选型 | 说明 |
|---|---|---|
| 语言 | Python 3.10+ | |
| AI 模型 | Anthropic Claude | 通过官方 `anthropic` SDK |
| 推荐模型 | Claude Sonnet (claude-sonnet-4-5) | 平衡成本与质量;Haiku 用于测试 |
| 数据校验 | `pydantic` v2 | 强制 JSON 结构 |
| 搜索引擎 | Brave Search API | 用户自备 API key |
| 工具调用 | Anthropic tool use (custom tool) | 把 Brave 包装成 Claude 的自定义工具 |
| 文档生成 | MkDocs + Material 主题 | `mkdocs-material` |
| 数学公式 | KaTeX (通过 `pymdown-extensions` 的 `arithmatex`) | |
| 配置管理 | `python-dotenv` + `pydantic-settings` | `.env` 文件存 API key |
| 命令行 | `click` 或 `argparse` | 二选一,推荐 `click` |
| 日志 | `rich` | 进度条 + 彩色日志 |
| 测试 | `pytest` | 仅核心模块需要测试 |

## 3. 项目目录结构(必须遵守)

```
exam-in-mind/
├── SPEC.md                    # 本文件
├── PLAN.md                    # 分阶段实施计划
├── README.md                  # 用户使用说明(Phase 8 生成)
├── .env.example               # API key 模板
├── .env                       # 实际 API key(gitignore)
├── .gitignore
├── pyproject.toml             # 依赖管理
├── config.yaml                # 运行时配置(模型、层级、开关等)
│
├── exam_in_mind/              # 主代码包
│   ├── __init__.py
│   ├── main.py                # 命令行入口
│   ├── config.py              # 配置加载
│   ├── models.py              # Pydantic 数据模型(KnowledgeNode 等)
│   ├── llm_client.py          # Anthropic API 封装
│   ├── brave_search.py        # Brave Search API 封装
│   ├── tools.py               # Claude 自定义工具定义(包装 brave_search)
│   ├── cache.py               # JSON 缓存读写
│   ├── prompts.py             # 所有 prompt 模板
│   ├── builders/
│   │   ├── __init__.py
│   │   ├── outline_builder.py    # 宏观框架构建器(Phase 4)
│   │   ├── tree_builder.py       # 递归分解器(Phase 5)
│   │   └── content_builder.py    # 叶子内容生成器(Phase 6)
│   └── renderers/
│       ├── __init__.py
│       ├── markdown_renderer.py  # 单文件 Markdown 输出
│       └── mkdocs_renderer.py    # MkDocs 站点输出
│
├── tests/
│   ├── test_brave_search.py
│   ├── test_models.py
│   └── test_cache.py
│
└── output/                    # 生成结果(gitignore)
    └── ap_calc_bc/
        ├── site/              # MkDocs 编译产物
        ├── docs/              # MkDocs 源文件
        ├── full.md            # 单文件 Markdown
        ├── tree.json          # 知识树原始数据(缓存)
        └── run.log            # 运行日志
```

## 4. 核心数据结构

```python
# exam_in_mind/models.py

from pydantic import BaseModel, Field
from typing import Optional

class KnowledgeNode(BaseModel):
    """知识树节点"""
    id: str = Field(..., description="层级编号,如 '1', '1.2', '1.2.3'")
    title: str = Field(..., description="节点标题")
    level: int = Field(..., ge=1, le=3, description="1=章, 2=节, 3=知识点")
    summary: str = Field(..., description="一句话简介")
    importance: int = Field(default=3, ge=1, le=5, description="考试重要度 1-5")
    children: list["KnowledgeNode"] = Field(default_factory=list)
    content: Optional["LeafContent"] = Field(default=None, description="仅叶子节点填充")

class LeafContent(BaseModel):
    """叶子知识点的详细内容"""
    definition: str = Field(..., description="知识点定义,支持 LaTeX")
    formulas: list[str] = Field(default_factory=list, description="核心公式/定理列表,LaTeX")
    common_mistakes: list[str] = Field(default_factory=list, description="易错点列表")
    sources: list[str] = Field(default_factory=list, description="引用来源 URL(可选)")

class ExamTree(BaseModel):
    """完整知识树根对象"""
    exam_name: str
    language: str
    generated_at: str  # ISO timestamp
    root_nodes: list[KnowledgeNode]
    metadata: dict = Field(default_factory=dict)  # 考纲版本、模型名等
```

## 5. 核心流程(8 步)

```
[用户命令] python -m exam_in_mind --exam "AP Calculus BC" --lang zh
        ↓
[Step 1] 加载配置 + 校验 API key
        ↓
[Step 2] 检查缓存 → 若有 tree.json 且未过期,询问是否复用
        ↓
[Step 3] 调用 outline_builder
        - 启用 Brave Search 工具
        - prompt: "查询 AP Calculus BC 最新 CED 考纲,返回一级 Unit 列表"
        - 输出: list[KnowledgeNode] (level=1, children=[])
        - 保存到 tree.json (阶段性快照)
        ↓
[Step 4] 调用 tree_builder.expand_to_level_2()
        - 关闭搜索
        - 对每个 level=1 节点,调用 Claude 生成 level=2 子节点
        - 传入父节点信息 + 兄弟节点列表(去重)
        - 保存快照
        ↓
[Step 5] 调用 tree_builder.expand_to_level_3()
        - 同上,生成 level=3 知识点节点
        - 保存快照
        ↓
[Step 6] 调用 content_builder
        - 对每个 level=3 叶子节点,调用 Claude 生成 LeafContent
        - 强制返回 JSON (用 tool use 或 response_format)
        - 进度条显示 X/Y
        - 每完成 N 个保存一次快照(断点续跑)
        ↓
[Step 7] 调用 markdown_renderer → 输出 full.md
        ↓
[Step 8] 调用 mkdocs_renderer → 生成 docs/ → 执行 mkdocs build → 输出 site/
        ↓
[完成] 打印产出物路径
```

## 6. 搜索方案细节

- **实现方式**: Brave Search API 包装成 Claude 的 custom tool
- **工具名**: `search_web`
- **工具参数**: `{"query": str, "count": int (default 5)}`
- **调用位置**: 仅在 `outline_builder` 启用 (Step 3)
- **配置开关**: `config.yaml` 中 `search.enabled: true/false`,默认 true
- **结果处理**: 把 Brave 返回的标题+摘要+URL 整理成文本返回给 Claude;同时记录 URL 到 `LeafContent.sources`(若适用)
- **错误处理**: Brave API 失败时降级为"无搜索模式",打印警告但不中断流程

## 7. 缓存与断点续跑

- **缓存文件**: `output/{exam_slug}/tree.json`
- **快照时机**: 每完成一个 Step 后写入
- **断点续跑**: 启动时检测 tree.json,若存在则:
  - 找到最后完成的 step
  - 询问用户: "检测到上次进度到 Step X,是否继续? [Y/n/restart]"
  - 继续: 从下一步开始
  - restart: 备份旧文件后重新开始
- **手动修正**: 用户可手动编辑 tree.json,程序识别后只重跑后续步骤

## 8. 配置文件 (config.yaml)

```yaml
# Anthropic API
llm:
  model: "claude-sonnet-4-5"  # 测试时可改为 claude-haiku-4-5
  max_tokens: 4096
  temperature: 0.3            # 知识类任务用低温度

# Brave Search
search:
  enabled: true
  provider: "brave"
  results_per_query: 5

# 知识树参数
tree:
  max_depth: 3                # 章/节/知识点
  level_1_count_hint: "8-12"  # 仅作为 prompt 提示
  level_2_count_hint: "4-8"
  level_3_count_hint: "3-6"

# 输出
output:
  base_dir: "./output"
  formats: ["mkdocs", "markdown"]  # 同时生成两种
  language: "zh"               # 默认中文,命令行可覆盖

# 日志
logging:
  level: "INFO"
  file: "run.log"
```

## 9. .env 文件模板 (.env.example)

```
ANTHROPIC_API_KEY=sk-ant-xxxxx
BRAVE_SEARCH_API_KEY=BSAxxxxx
```

## 10. 命令行接口

```bash
# 基本用法
python -m exam_in_mind --exam "AP Calculus BC"

# 完整参数
python -m exam_in_mind \
  --exam "AP Calculus BC" \
  --lang zh \
  --model claude-sonnet-4-5 \
  --no-search \
  --restart \
  --output-dir ./output
```

参数:
- `--exam` (必填): 考试名称
- `--lang`: 输出语言,默认 zh
- `--model`: 覆盖 config.yaml 中的模型
- `--no-search`: 禁用 Brave Search
- `--restart`: 忽略缓存重新开始
- `--output-dir`: 自定义输出目录
- `--verbose`: 详细日志

## 11. 产出物清单

每次运行结束后,`output/{exam_slug}/` 下应有:

| 文件 | 用途 |
|---|---|
| `site/index.html` | MkDocs 静态站首页(双击打开) |
| `site/` 整个文件夹 | 可离线浏览的复习网站 |
| `full.md` | 单文件 Markdown,可导入 Obsidian/Notion |
| `tree.json` | 知识树原始数据(缓存+可手动编辑) |
| `docs/` | MkDocs 源 Markdown 文件 |
| `mkdocs.yml` | MkDocs 配置文件 |
| `run.log` | 本次运行日志 |

## 12. 代码规范

- **注释**: 中文注释,关键函数必须有 docstring 说明用途、参数、返回值
- **类型标注**: 所有函数必须有完整 type hints
- **错误处理**: API 调用必须 try/except,失败时打印清晰错误信息
- **日志**: 使用 `rich.console.Console` 输出彩色日志,关键步骤打印进度
- **常量**: prompt 模板放 `prompts.py`,不写死在业务代码里
- **避免**: 不要引入 SPEC 未列出的新依赖;不要自作主张加 Web 界面、数据库、ORM

## 13. 不做的事(明确边界)

- ❌ 不做 Web 界面(Streamlit/Gradio/FastAPI)
- ❌ 不做用户系统、登录、多用户隔离
- ❌ 不做数据库(JSON 文件够用)
- ❌ 不做 Docker 化
- ❌ 不做 CI/CD
- ❌ 不生成图片(连 Mermaid 都暂不做)
- ❌ 不做前置知识依赖图(prerequisites)
- ❌ 不做单元测试以外的复杂测试体系

## 14. 验收标准(整体)

项目完成后,执行:
```bash
python -m exam_in_mind --exam "AP Calculus BC"
```
应能:
1. 不报错地跑完全流程
2. 生成的 `site/index.html` 用浏览器打开后,左侧有完整的章/节/知识点树
3. 每个知识点页面有定义、公式(LaTeX 正确渲染)、易错点
4. 顶部搜索框可搜索关键词
5. `full.md` 可被 VS Code / Obsidian 正常打开
6. 重新运行同一命令时,提示"检测到缓存,是否复用"
