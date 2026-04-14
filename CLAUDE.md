# CLAUDE.md - Exam-in-Mind 项目开发准则

> 本文件是 Claude Code 在本项目中的行为准则。每次开始工作前,请先阅读并遵守。

## 🎯 项目身份

Exam-in-Mind 是一个面向特定考试科目的学习智能体,目标是自动构建分层知识树并输出为 MkDocs 静态站。

## 📚 必读文档

开始任何工作前,先确认你已熟悉以下文档:

- **PLAN.md** — 当前迭代期的协作流程与 task 循环说明。可随 task 演进修改。
- **SPEC.md** — 项目身份、核心数据结构、核心流程。可随 task 演进修改。
- **devlog/versions/v{当前}-dev.md** — 当前版本的日常开发日志,每次 commit 必须同步维护。
- **archive/PLAN.v1.0-phases.md** — 建造期(v1.0.0 前 8 Phase)历史档案,仅供回顾。
- **devlog/phase-1~8-*.md** — 建造期各 Phase 的详细复盘,只读历史存档。

如果你不确定某个技术决策,**先去 SPEC.md 找答案**;不确定流程问题,**先去 PLAN.md 找答案**,而不是自己发挥。

## 🚦 核心工作原则

### 1. 严格按 task 边界工作
- 每个 task 开工前必须与用户确认修改计划和范围(PLAN.md §3 的 6 步循环)
- 不擅自扩大改动范围——"顺手优化"、"主动重构"都属于**新的** task,必须单独确认
- Task 实施过程中发现计划外的问题,**停下来问用户**,不自行处理
- 不连续执行多个 task,每个 task 完成后等用户验收

### 2. 不越界
- 新增/更换依赖必须作为独立 task 与用户确认
- 遇到 SPEC / PLAN 没明确规定的情况,**停下来问用户**,不要自作主张
- 需要改动 `PLAN.md` / `SPEC.md` / `CLAUDE.md` 本身时,与普通 task 同等对待(改前确认计划)
- `archive/` 和 `devlog/phase-*.md` 等历史档案**只读**,永不修改

### 3. 沟通透明
- 所有解释和报告使用**中文**
- 代码注释使用**中文**,关键函数必须有 docstring
- 遇到报错时,**先解释原因,再修复**,绝不盲目重试
- 完成每个 task 后给一份"完成报告":创建/修改了哪些文件、如何验收、已知局限

## 💾 Git 版本管理规则

### 强制 commit 时机(无需用户提醒)
- 每个新文件创建并写完初版后
- 任何破坏性操作前(重写超过 50% 的现有文件、删除文件、重构目录)
- 每次成功跑通一个验收命令后
- 每次 bug 修复完成后
- 连续工作超过 30 分钟时(兜底机制,以你的感知为准)
- Task 内每完成一个明显的子任务时(函数级别 / 文件级别)
- Task 最终完成时(代码 commit + devlog 同步;如需发版再走封版流程)

### Commit message 格式
```
<类型>(<范围>): <简短描述>
```

类型必须是: `feat` / `fix` / `refactor` / `docs` / `chore` / `test` / `wip`

示例:
- `feat(renderer): add scroll arrow buttons to top navigation tabs`
- `fix(content_builder): handle empty LaTeX formula list`
- `docs(devlog): record sidebar scroll fix in v1.0.1`

### 代码与版本日志的处理

迭代期的日志模式(详见 PLAN.md §3 循环 [6] 和"📝 开发日志规则"):
**代码 + 版本日志(`devlog/versions/v{当前}-dev.md`)可以在同一 commit 里一起 add**,commit 后 amend 真实 hash 到占位符。

Task 完成的标准 commit 序列:
```bash
# 1. 代码完成,验收通过
#    同时确认 devlog/versions/v{当前}-dev.md 已追加记录(hash 先用占位符)
git add <代码文件> devlog/versions/v{当前}-dev.md
git commit -m "<type>(<scope>): <简短描述>"

# 2. 用真实 hash 替换占位符,amend
git commit --amend --no-edit
#   (或在下一次 commit 里补修正)

# 3. 若达到封版条件(用户拍板),才走封版流程:
#    更新 CHANGELOG.md、VERSION、打 v{版本号} tag、新建下一版本 dev 日志
```

> **历史说明**:v1.0.0 建造期采用"代码 commit → 等验收 → devlog 单独 commit → 打 phase-X-complete tag"的严格分离模式。该模式已归档,迭代期不再使用 `phase-X-complete` tag。

### Commit 前必检
执行 `git status` 并确认:
- `.env` 不在待提交列表
- `output/` 不在待提交列表  
- `.venv/` 不在待提交列表
- 待提交文件与 commit message 的"类型+范围"描述吻合(代码改动 + 同次 task 对应的版本日志记录可在同一 commit;但不要把**无关**的文件打包混提)

异常情况停下来问用户,不要擅自处理。

## 🛡️ 安全红线(永不触碰)

- ❌ 不执行 `git reset --hard` 或 `git push --force`
- ❌ 不执行 `git clean -fd` 或类似删除未追踪文件的命令
- ❌ 不在对话中显示 `.env` 文件的内容或任何 API key
- ❌ 不删除 SPEC.md / PLAN.md / CLAUDE.md / devlog/ / archive/ 下的任何文件
- ❌ 不修改用户已经手动编辑过的配置文件(除非用户明确要求)

需要执行任何危险操作前,**先描述意图并等用户确认**。

## 📝 开发日志规则

本项目采用**双层日志体系**,当前只写第 1 类:

### 1. 版本开发日志(当前在用)

文件位置: `devlog/versions/v{版本号}-dev.md`

模板: `devlog/VERSION_LOG_TEMPLATE.md`

**核心规则: 每次 commit 都要在版本日志里留痕。**

### 2. Phase 日志(历史存档,只读)

文件位置: `devlog/phase-{编号}-{主题}.md`(及对应模板 `archive/devlog-TEMPLATE.phase.md`)

仅存在于 v1.0.0 开发期(Phase 1-8)的历史记录。**v1.0.0 发布后不再新增 Phase 日志**,现有文件作为历史存档永久保留,不得修改。

**记录粒度**:

| Commit 类型 | 记录方式 |
|---|---|
| `feat` 新功能 | 完整三段式(问题/做法/效果) |
| `fix` bug 修复 | 完整三段式 |
| `refactor` 重构 | 完整三段式 |
| `perf` 性能 | 完整三段式 |
| `docs` 文档 | 一行索引(除非是重要文档大改) |
| `chore` 杂项 | 一行索引 |
| `test` 测试 | 一行索引 |
| `wip` 临时 | 一行索引 |

**格式约束**:
- 主要变更每条最多 4 行(标题 + 问题 + 做法 + 效果)
- 效果行必须带 emoji: ✅ / ⚠️ / ❌ / 🔄
- 按日期分组
- 文字精炼,拒绝啰嗦

**commit 与日志的同步**:

每次代码变更的标准流程:
1. 完成代码改动
2. 更新 `devlog/versions/v{当前版本}-dev.md` 添加对应记录(初次不知道 hash,用占位符)
3. 一起 `git add` 代码文件和日志文件
4. `git commit` 后,**立刻**把占位符替换为真实 commit hash,再做一次 amend:
```bash
   git commit --amend --no-edit
```
   或者在下一次 commit 时补充修正

**版本封版流程**:

当一个版本准备发布时:
1. 在 v{版本}-dev.md 文件末尾填写"版本总结"章节
2. 把"版本周期"的"进行中"改为实际结束日期
3. 更新 CHANGELOG.md 添加新版本条目
4. 更新 VERSION 文件
5. commit 变更,message: `chore(release): v{版本号}`
6. 打 git tag: `git tag -a v{版本号} -m "{简短说明}"`
7. 立即创建下一个版本的 dev 日志文件(`v{新版本}-dev.md`),留空等待填充

## 🔄 应急恢复策略

如果用户要求"回退到之前状态",默认采用**非破坏性回退**:

1. 先 `git log --oneline` 让用户选择目标 commit
2. 询问:"完全回退所有文件" 还是 "只回退代码,保留 devlog"?
3. **推荐"只回退代码"**(保留失败经验作为博客素材)
4. 操作前再次确认
5. 操作后立刻 commit 当前状态作为新历史节点
   message 格式: `chore(rollback): rollback code to <hash>, retain devlog`

## ⚙️ 环境约定

- 操作系统: Windows
- Python: 3.10+
- 虚拟环境: 项目根目录的 `.venv/`,激活命令 `.venv\Scripts\activate`
- 包安装: `pip install -e ".[dev]"`
- 主命令: `python -m exam_in_mind --exam "<考试名>" --lang zh`

## 🛠️ 常用命令

```bash
# 安装(含开发依赖)
pip install -e ".[dev]"

# 主入口(等价于 console script `exam-in-mind`)
python -m exam_in_mind --exam "AP Calculus BC" --lang zh

# 常用调试组合
python -m exam_in_mind --exam "SAT Math" --model claude-haiku-4-5-20251001 --no-search --verbose
python -m exam_in_mind --exam "AP Calculus BC" --restart   # 忽略缓存重跑

# 测试(pyproject 已设 testpaths=["tests"])
pytest                                  # 全量
pytest tests/test_cache.py              # 单文件
pytest tests/test_models.py::test_xxx   # 单用例
pytest -k "brave" -v                    # 关键字过滤

# 仅渲染(手动改完 tree.json 后)— 通过 --restart 反向操作不行,
# 需直接调用 renderer 模块或保留 tree.json 让程序识别断点
mkdocs serve -f output/<slug>/mkdocs.yml   # 本地预览生成的站点
```

注意:本仓库**没有配置 lint/format 工具**(无 ruff/black/mypy),不要假设它们存在。

## 🏗️ 架构速览

整个流水线是**线性 8 步 + JSON 快照断点**(详见 SPEC.md §5),代码按职责分层:

```
main.py (CLI入口)
  └─ config.py  ← .env + config.yaml(pydantic-settings)
  └─ cache.py   ← output/<slug>/tree.json 读写 + 断点检测
  └─ builders/  ← 三段式构建,每段产出后立即写快照
       ├─ outline_builder    Step 3: 联网查考纲 → level=1 节点
       ├─ tree_builder       Step 4-5: 递归扩到 level=2、level=3
       └─ content_builder    Step 6: 叶子节点生成 LeafContent
  └─ renderers/ ← 同一棵 ExamTree 双格式渲染
       ├─ markdown_renderer  → full.md
       └─ mkdocs_renderer    → docs/ + mkdocs.yml + site/
```

**横切依赖**:
- `llm_client.py`:封装 Anthropic SDK,负责 tool-use 循环(供 outline_builder 调用 search)
- `brave_search.py`:Brave API 原始封装(httpx);失败时降级为 no-search,不中断
- `tools.py`:把 brave_search 包装成 Claude 自定义工具 `search_web`
- `prompts.py`:**所有** prompt 模板集中在此,业务代码不许写死字符串
- `models.py`:`KnowledgeNode` / `LeafContent` / `ExamTree`(pydantic v2,递归结构)

**核心数据流**:从头到尾只有一个对象在传递 —— `ExamTree`。每个 builder 接收上一步的树,**就地扩展**而非重建,保证断点续跑时拿同一份 `tree.json` 能从任意 step 继续。

**搜索的边界**:Brave Search **只在 outline_builder 启用**(SPEC §6)。tree_builder 和 content_builder 一律关闭联网,纯靠模型内置知识 + 父节点上下文。改动这条边界前必须先和用户确认。

**配置三层叠加优先级**(高 → 低):CLI 参数 > `config.yaml` > 代码默认值。`.env` 只放 secret(2 个 key)。

## 🤝 与用户的互动节奏

用户角色: 产品经理 + 验收官,不一定写代码,但所有决策由他做出。

每个 task 的标准 6 步循环(完整定义见 `PLAN.md` §3):

1. **用户提出需求/bug**
2. **Claude 复述并确认范围,与用户共同设计修改计划**
   `"我理解你想要 ___,改动会涉及 ___,确认开工?"`
3. **用户审核通过修改计划后,Claude 实施**
   - 同步在 `devlog/versions/v{当前}-dev.md` 写记录(hash 用占位符)
4. **Claude 完成报告**:改了哪些文件、怎么验收、已知限制
5. **用户验收**(Claude 辅助:提供验收命令、指明关注点)
6. **commit**(代码 + 日志一起 add,commit 后 amend 真实 hash)

不在节奏内的事(比如新需求、规则变更、顺手优化),**先停下来确认**,作为新 task 处理。

---

**最后提醒**: 当你不确定该怎么做时,默认选择是 **"停下来问用户"**,而不是 "自己发挥"。
