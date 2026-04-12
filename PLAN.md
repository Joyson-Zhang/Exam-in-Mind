# Exam-in-Mind 分阶段实施计划 (PLAN)

> 本计划把项目拆成 8 个 Phase。每个 Phase 必须停下来等用户验收后才能进入下一个。
> 严禁连续执行多个 Phase。严禁跳过验收标准。

## 总览

| Phase | 目标 | 预计耗时 |
|---|---|---|
| 1 | 项目脚手架 + 配置系统 | 15 min |
| 2 | Brave Search 模块 + 工具封装 | 20 min |
| 3 | 数据模型 + 缓存系统 | 15 min |
| 4 | 宏观框架构建器(带搜索) | 25 min |
| 5 | 递归分解器(level 2 → 3) | 25 min |
| 6 | 叶子内容生成器 | 25 min |
| 7 | Markdown + MkDocs 渲染器 | 25 min |
| 8 | 主流程串联 + README + 端到端测试 | 30 min |

---

## Phase 1: 项目脚手架 + 配置系统

### 目标
搭建项目骨架,让用户能装依赖、配置 API key、运行一个空的命令行入口。

### 交付物
- [ ] 完整的目录结构(按 SPEC 第 3 节)
- [ ] `pyproject.toml`(列出所有依赖)
- [ ] `.env.example` + `.gitignore`
- [ ] `config.yaml`(按 SPEC 第 8 节)
- [ ] `exam_in_mind/config.py` (用 pydantic-settings 加载 .env + yaml)
- [ ] `exam_in_mind/main.py` (用 click 定义命令行参数,目前只打印参数)
- [ ] 各子模块的空 `__init__.py` 和占位文件

### 验收命令
```bash
pip install -e .
python -m exam_in_mind --exam "AP Calculus BC" --verbose
```
应输出:加载到的配置内容 + 接收到的命令行参数,不报错。

### 验收标准
- 目录结构与 SPEC 第 3 节完全一致
- 缺少 .env 时给出友好提示而非崩溃
- 命令行 `--help` 能列出 SPEC 第 10 节的所有参数

---

## Phase 2: Brave Search 模块 + 工具封装

### 目标
实现 Brave Search API 调用,并封装为 Claude 可调用的 custom tool。

### 交付物
- [ ] `exam_in_mind/brave_search.py`
  - 函数 `search(query: str, count: int = 5) -> list[dict]`
  - 返回 `[{title, url, description}, ...]`
  - 处理 API 错误、限流、空结果
- [ ] `exam_in_mind/tools.py`
  - 定义 Claude tool schema: `search_web`
  - 实现 tool dispatcher: 接收 Claude 的 tool_use 请求 → 调 brave_search → 返回 tool_result
- [ ] `tests/test_brave_search.py`
  - 至少 2 个测试: 正常查询、API key 错误处理(可 mock)

### 验收命令
```bash
python -m exam_in_mind.brave_search "AP Calculus BC official CED"
pytest tests/test_brave_search.py -v
```
应:打印出 5 条搜索结果,包含 title/url/description;测试全部通过。

### 验收标准
- Brave API 失败时不崩溃,打印警告并返回空列表
- tool schema 符合 Anthropic tool use 规范

---

## Phase 3: 数据模型 + 缓存系统

### 目标
实现知识树的 Pydantic 模型和 JSON 缓存读写。

### 交付物
- [ ] `exam_in_mind/models.py` (按 SPEC 第 4 节定义 KnowledgeNode / LeafContent / ExamTree)
- [ ] `exam_in_mind/cache.py`
  - `save_tree(tree: ExamTree, path: Path)` → 写 tree.json
  - `load_tree(path: Path) -> ExamTree | None`
  - `get_progress(tree: ExamTree) -> int` → 返回当前到第几步
- [ ] `tests/test_models.py` + `tests/test_cache.py`
  - 测试: 创建树 → 保存 → 加载 → 验证一致性

### 验收命令
```bash
pytest tests/test_models.py tests/test_cache.py -v
```

### 验收标准
- Pydantic 模型严格符合 SPEC 第 4 节
- tree.json 是人类可读的(indent=2, ensure_ascii=False)
- 加载损坏的 JSON 时给友好错误,不崩溃

---

## Phase 4: 宏观框架构建器

### 目标
实现"调用 Claude + Brave Search,生成一级 Unit 列表"。

### 交付物
- [ ] `exam_in_mind/llm_client.py`
  - 封装 Anthropic API 调用
  - 支持 tool use 循环(收到 tool_use → 执行 → 返回 tool_result → 再调 Claude)
  - 强制 JSON 输出(用 tool use 模式)
- [ ] `exam_in_mind/prompts.py`
  - `OUTLINE_BUILDER_PROMPT`: 让 Claude 调用 search_web 查询考纲并返回 level=1 节点 JSON
- [ ] `exam_in_mind/builders/outline_builder.py`
  - 函数 `build_outline(exam_name: str, lang: str) -> list[KnowledgeNode]`
  - 启用 search_web 工具
  - 返回带 level=1 的节点列表(children 为空)
- [ ] 集成到 `main.py`: 命令行跑完后保存 tree.json

### 验收命令
```bash
python -m exam_in_mind --exam "AP Calculus BC" --lang zh
```
应:看到搜索调用日志 → 生成 8-12 个一级 Unit → 写入 `output/ap_calculus_bc/tree.json`。

### 验收标准
- tree.json 中有 root_nodes,每个节点 level=1, title 是合理的 AP Calc BC Unit 名
- 节点的 importance 已合理填充
- 控制台日志清晰显示每一步进展

---

## Phase 5: 递归分解器

### 目标
把 level=1 的树扩展到 level=3 (章 → 节 → 知识点)。

### 交付物
- [ ] `exam_in_mind/prompts.py` 新增:
  - `EXPAND_TO_LEVEL_2_PROMPT` (输入父节点 + 兄弟节点列表)
  - `EXPAND_TO_LEVEL_3_PROMPT`
- [ ] `exam_in_mind/builders/tree_builder.py`
  - `expand_to_level_2(tree: ExamTree) -> ExamTree`
  - `expand_to_level_3(tree: ExamTree) -> ExamTree`
  - 每完成一个父节点保存一次快照
  - 进度条(用 rich)
- [ ] `main.py` 串联: outline → level_2 → level_3,每步保存

### 验收命令
```bash
python -m exam_in_mind --exam "AP Calculus BC" --lang zh
```
应:看到层层扩展的进度条;最终 tree.json 中每个一级节点下有 4-8 个二级节点,每个二级下有 3-6 个三级节点。

### 验收标准
- 不重复生成同名节点
- 节点 id 编号正确(如 "2.3.1")
- 中断后重跑能从断点继续(测试: 跑到一半 Ctrl+C, 重新跑应继续)

---

## Phase 6: 叶子内容生成器

### 目标
为每个 level=3 叶子节点生成 LeafContent(定义、公式、易错点)。

### 交付物
- [ ] `exam_in_mind/prompts.py` 新增 `GENERATE_LEAF_CONTENT_PROMPT`
- [ ] `exam_in_mind/builders/content_builder.py`
  - `generate_all_leaves(tree: ExamTree) -> ExamTree`
  - 遍历所有 level=3 节点,调用 Claude 生成 LeafContent
  - 强制 JSON 输出
  - 每完成 5 个节点保存一次快照
  - rich 进度条显示 X/Y
- [ ] `main.py` 串联

### 验收命令
```bash
python -m exam_in_mind --exam "AP Calculus BC" --lang zh
```
应:看到 "生成叶子内容 45/120" 之类的进度;最终 tree.json 每个叶子节点的 content 字段已填充。

### 验收标准
- 公式字段使用合法 LaTeX(如 `$\\frac{d}{dx}f(x)$`)
- 易错点至少 2 条
- 中断恢复正常工作

---

## Phase 7: Markdown + MkDocs 渲染器

### 目标
把 tree.json 渲染成 full.md 和 MkDocs 静态站。

### 交付物
- [ ] `exam_in_mind/renderers/markdown_renderer.py`
  - `render_full_markdown(tree: ExamTree, output_path: Path)`
  - 单文件,有目录、章节标题、LaTeX 公式
- [ ] `exam_in_mind/renderers/mkdocs_renderer.py`
  - `render_mkdocs_site(tree: ExamTree, output_dir: Path)`
  - 生成 `mkdocs.yml`(配置 Material 主题、KaTeX、搜索)
  - 生成 `docs/` 目录下的分文件 Markdown
  - 调用 `mkdocs build` 命令生成 site/
- [ ] `main.py` 末尾调用两个渲染器

### 验收命令
```bash
python -m exam_in_mind --exam "AP Calculus BC" --lang zh
# 然后双击 output/ap_calculus_bc/site/index.html
```
应:浏览器打开看到带左侧目录树的网站,公式正确渲染,搜索框可用。`full.md` 用 VS Code 打开内容完整。

### 验收标准
- mkdocs.yml 正确配置 arithmatex 用于 LaTeX
- 章节文件路径符合 `docs/01-unit-name/01-section-name/01-knowledge-point.md`
- site/ 完全离线可用(不依赖 CDN, 或至少能正常显示)

---

## Phase 8: 主流程串联 + README + 端到端测试

### 目标
最终整理,生成 README,跑一次完整流程验收。

### 交付物
- [ ] `README.md`
  - 项目简介
  - 安装步骤(含 .env 配置)
  - 使用示例
  - 常见问题
  - 项目结构图
- [ ] 检查 main.py 整体流程清晰、日志完整
- [ ] 跑一次完整的 AP Calculus BC 生成
- [ ] 检查所有产出物符合 SPEC 第 11 节

### 验收命令
```bash
# 删除旧产出
rm -rf output/

# 全新一次端到端
python -m exam_in_mind --exam "AP Calculus BC" --lang zh

# 验证产出
ls output/ap_calculus_bc/
# 应有: site/ docs/ full.md tree.json mkdocs.yml run.log
```

### 验收标准
按 SPEC 第 14 节"整体验收标准"逐条检查通过。

---

## 通用规则(每个 Phase 都适用)

1. **开始 Phase 前**: 用一两句话告诉用户"我现在开始 Phase X,目标是 ___,将创建/修改这些文件: ___"
2. **执行中**: 遇到任何与 SPEC 不符的情况,停下来询问用户,不要自作主张
3. **结束 Phase 后**: 输出本 Phase 的"完成报告":
   - 创建/修改了哪些文件
   - 如何运行验收命令
   - 已知的局限或待办
4. **不要连续执行多个 Phase**。等用户明确说"通过,进入 Phase X+1"才继续。
5. **不要修改 SPEC.md 和 PLAN.md**,如需变更先与用户讨论。
6. **SPEC 补丁机制**: Claude 可以主动提出合理要求作为 SPEC 的补丁,但在征得用户同意前不得直接更改。
7. **开发日志**: 每个 Phase 结束、用户确认"通过"之后,立刻基于 `devlog/TEMPLATE.md` 创建本 Phase 的日志文件 `devlog/phase-{编号}-{简短主题}.md` 并填写完成。日志写完后再等用户说"开始下一个 Phase"。写日志只能修改 `devlog/` 下的文件,不得修改任何代码或配置文件;如发现代码问题,记录在"给下一个 Phase 的提醒"中。
