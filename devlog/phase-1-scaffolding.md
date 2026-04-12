# Phase 1 — 项目脚手架与配置系统

> 追溯补写。基于对本次对话的完整记忆撰写，力求真实。

---

## 基本信息

| 项目 | 内容 |
|---|---|
| Phase 编号 | 1 |
| 主题 | 项目脚手架与配置系统 |
| 开始时间 | 2026-04-11（具体时刻记忆不清） |
| 结束时间 | 2026-04-11（具体时刻记忆不清） |
| 实际耗时 | 约 30 分钟（含多轮调试） |

---

## 目标回顾

搭建项目骨架，让用户能装依赖、配置 API key、运行一个空的命令行入口。

---

## 实际完成情况

- [x] 完整的目录结构（按 SPEC 第 3 节）
- [x] `pyproject.toml`（列出所有依赖）
- [x] `.env.example` + `.gitignore`
- [x] `config.yaml`（按 SPEC 第 8 节）
- [x] `exam_in_mind/config.py`（用 pydantic-settings 加载 .env + yaml）
- [x] `exam_in_mind/main.py`（用 click 定义命令行参数，目前只打印参数）
- [x] 各子模块的空 `__init__.py` 和占位文件

**与计划的差异：**

新增了 `exam_in_mind/__main__.py`，SPEC/PLAN 未明确列出但属于必需文件（支持 `python -m exam_in_mind` 调用方式）。其余无偏差。

用户在验收阶段补充了一个开发实践要求：使用虚拟环境 `.venv`。这不在原始 PLAN 中，但属于合理的工程规范，当场执行并同步更新了 PLAN.md 通用规则。

---

## 关键决策记录

### 决策 1：pyproject.toml 的 build-backend 选型

- **背景**：需要一个现代 Python 包的构建配置
- **候选方案**：
  - 方案 A：`setuptools.backends.legacy:build`（较新写法）
  - 方案 B：`setuptools.build_meta`（兼容性更好的传统写法）
- **最终选择**：方案 A，后来被迫改为方案 B
- **理由**：最初写了方案 A，安装时报错 `BackendUnavailable: Cannot import 'setuptools.backends.legacy'`，说明用户 Python 环境的 setuptools 版本不支持该写法。改为方案 B 后立即解决。这是第一个犯错又改正的地方。

### 决策 2：`EnvSettings` 中使用 `alias` 还是字段名来映射环境变量

- **背景**：pydantic-settings 读取 `.env` 文件时，字段名和 `alias` 的优先级规则需要确认
- **候选方案**：
  - 方案 A：直接用字段名 `anthropic_api_key`，pydantic-settings 自动映射为 `ANTHROPIC_API_KEY`
  - 方案 B：显式写 `alias="ANTHROPIC_API_KEY"`
- **最终选择**：方案 B（写了 alias）
- **理由**：初始实现时选了方案 B，认为显式更清晰。但后来在验收阶段发现了 `env_ignore_empty` 缺失的 Bug（见下方问题记录），与 alias 本身关系不大，alias 写法本身没有造成问题。

### 决策 3：配置加载拆成两层（EnvSettings + AppConfig）

- **背景**：API key（敏感）和运行时配置（yaml）性质不同，需要分开处理
- **候选方案**：
  - 方案 A：全部用 pydantic-settings，yaml 也通过 env_file 或自定义 source 加载
  - 方案 B：API key 用 pydantic-settings（读 .env），yaml 用 PyYAML 手动加载，两者合并到 `AppConfig`
- **最终选择**：方案 B
- **理由**：yaml 配置结构较复杂（嵌套字典），pydantic-settings 处理嵌套 yaml 需要额外工作；而 PyYAML 直接读取更直观。两层分开也让职责更清晰。

---

## 遇到的问题与解决过程

### 问题 1：`setuptools.backends.legacy:build` 不可用

- **现象**：执行 `pip install -e ".[dev]"` 报错 `BackendUnavailable: Cannot import 'setuptools.backends.legacy'`
- **分析**：该写法是 setuptools 较新版本才引入的后端标识符，用户环境的 setuptools 版本较旧
- **解决**：将 `pyproject.toml` 的 `build-backend` 改为 `setuptools.build_meta`，立即解决

### 问题 2：Windows 终端中文乱码

- **现象**：程序运行后中文提示全部变成 `????` 乱码
- **分析**：Windows 终端默认编码为 GBK/CP936，而代码输出 UTF-8 字符串，两者不匹配
- **解决**：在 `__main__.py` 中检测 `sys.platform == "win32"` 时，将 `sys.stdout` 和 `sys.stderr` 替换为 `io.TextIOWrapper(..., encoding="utf-8")`。这让 rich 的输出能够正确编码

### 问题 3：Anthropic API Key 被系统环境变量覆盖（验收阶段发现）

- **现象**：用户填入 `.env` 文件后，程序仍显示 `Anthropic Key: 未配置`
- **分析**：Claude Code 运行环境将 `ANTHROPIC_API_KEY` 设置为空字符串（0字符）注入系统环境变量。pydantic-settings 默认优先使用系统环境变量，空字符串覆盖了 `.env` 文件中的真实值。Brave Key 没有这个问题，因为系统环境中没有预设 `BRAVE_SEARCH_API_KEY`
- **解决**：在 `EnvSettings.model_config` 中加入 `env_ignore_empty=True`，让 pydantic-settings 忽略空字符串的系统环境变量，转而使用 `.env` 文件中的值

这是整个 Phase 1 中最隐蔽的问题。如果用户没有亲自验收、只看"不崩溃"这一标准，这个 Bug 会直到 Phase 4 调用 Claude API 时才暴露，届时排查会更困难。

---

## 关键代码片段

### 片段 1：env_ignore_empty 修复

```python
model_config = SettingsConfigDict(
    env_file=ROOT_DIR / ".env",
    env_file_encoding="utf-8",
    env_ignore_empty=True,   # 系统环境变量为空字符串时忽略，改用 .env 文件中的值
    extra="ignore",
)
```

**为什么这样写：** Claude Code 环境会预设空的 `ANTHROPIC_API_KEY`，不加这个选项会导致用户配置的真实 key 被静默覆盖。这是 pydantic-settings v2 一个需要显式处理的行为。

### 片段 2：Windows UTF-8 输出修复

```python
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
```

**为什么这样写：** 替换底层 buffer 的 wrapper 是在不改变 rich 库调用方式的前提下统一修复编码问题的最小侵入方案。`errors="replace"` 确保遇到真正无法编码的字符时不崩溃。

### 片段 3：AppConfig 的两层加载结构

```python
class AppConfig:
    def __init__(self, yaml_path=None, verbose=False):
        # 第一层：pydantic-settings 读取 .env（敏感信息）
        env = EnvSettings()
        self.anthropic_api_key = env.anthropic_api_key

        # 第二层：PyYAML 读取 config.yaml（运行时配置）
        raw = self._load_yaml(yaml_path or ROOT_DIR / "config.yaml")
        self.llm = LLMConfig(raw.get("llm", {}))
        # ...
```

**为什么这样写：** 敏感信息和运行时配置分开处理，各自用最适合的工具。yaml 的嵌套结构用简单的 dict 类包装，避免引入额外的 pydantic-settings yaml source 依赖。

---

## 可作为博客素材的亮点

- **环境变量被静默覆盖的坑**：Claude Code 开发环境会预设空的 `ANTHROPIC_API_KEY`，导致用户配置的 key 被 pydantic-settings 忽略。这个问题只有在真正验收时才暴露，说明"不崩溃"≠"功能正确"，验收标准要具体到功能行为层面。
- **虚拟环境是补丁需求**：用户在验收前临时提出使用 `.venv`，这是一个典型的"SPEC 补丁"场景——合理、不破坏现有设计，当场执行并同步更新文档。

---

## 复盘与反思

- **如果重来**：应该在写 `pyproject.toml` 之前先检查用户的 Python/setuptools 版本，避免因构建后端写法不兼容导致第一步就失败。
- `env_ignore_empty=True` 应该是在 Claude Code 环境下开发所有 pydantic-settings 项目的默认选项，值得固化到模板里。
- Windows 编码修复放在 `__main__.py` 是合适的，但如果项目后续有更多入口点，需要注意每个入口都要处理。

---

## 给下一个 Phase 的提醒

- [ ] Phase 2 开始前确认 Brave Search API key 可用（可先用 `curl` 或 Python 脚本直接测试）
- [ ] `brave_search.py` 需要处理 Brave API 的限流（429）和网络超时，这在 SPEC 第 6 节有明确要求
- [ ] `tools.py` 的 Claude tool schema 格式要严格符合 Anthropic tool use 规范，建议直接对照官方文档写，不要凭记忆
- [ ] 注意：`exam_in_mind/config.py` 中的 `AppConfig` 在后续 Phase 中会被多个模块 import，确保它是无副作用的（不能在 import 时触发 API 调用或文件写入）
