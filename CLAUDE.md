# CLAUDE.md - Exam-in-Mind 项目开发准则

> 本文件是 Claude Code 在本项目中的行为准则。每次开始工作前,请先阅读并遵守。

## 🎯 项目身份

Exam-in-Mind 是一个面向特定考试科目的学习智能体,目标是自动构建分层知识树并输出为 MkDocs 静态站。

## 📚 必读文档

开始任何工作前,先确认你已熟悉以下文档:

- **SPEC.md** — 项目技术规格(架构、技术栈、数据结构、目录结构)。**不可修改**,如需变更必须先与用户讨论。
- **PLAN.md** — 8 个 Phase 的实施计划和验收标准。**不可修改**。
- **devlog/** — 每个 Phase 完成后的开发日志,用于复盘和未来的博客素材。

如果你不确定某个技术决策,**先去 SPEC.md 找答案**,而不是自己发挥。

## 🚦 核心工作原则

### 1. 严格分阶段
- 一次只做一个 Phase,**严禁连续执行多个 Phase**
- 每个 Phase 完成后停下来等用户验收,绝不擅自进入下一个
- 每个 Phase 开始前,先向用户说明:"我现在开始 Phase X,目标是 ___,将创建/修改这些文件: ___"

### 2. 不越界
- 不引入 SPEC 第 2 节技术栈列表之外的依赖
- 不做 SPEC 第 13 节"不做的事"列表里的任何事(尤其是 Web 界面、数据库、Docker)
- 遇到 SPEC 没明确规定的情况,**停下来问用户**,不要自作主张
- "顺手优化"和"主动重构"必须先经过用户同意

### 3. 沟通透明
- 所有解释和报告使用**中文**
- 代码注释使用**中文**,关键函数必须有 docstring
- 遇到报错时,**先解释原因,再修复**,绝不盲目重试
- 完成每个 Phase 后给一份完整的"完成报告":创建/修改了哪些文件、如何验收、已知局限

## 💾 Git 版本管理规则

### 强制 commit 时机(无需用户提醒)
- 每个新文件创建并写完初版后
- 任何破坏性操作前(重写超过 50% 的现有文件、删除文件、重构目录)
- 每次成功跑通一个验收命令后
- 每次 bug 修复完成后
- 连续工作超过 30 分钟时(兜底机制,以你的感知为准)
- Phase 内每完成一个明显的子任务时
- Phase 最终完成时(代码 commit + 等用户验收 + devlog commit + 打 tag)

### Commit message 格式
```
<类型>(<范围>): <简短描述>
```

类型必须是: `feat` / `fix` / `refactor` / `docs` / `chore` / `test` / `wip`

示例:
- `feat(builders): implement outline_builder with Brave Search`
- `fix(content_builder): handle empty LaTeX formula list`
- `docs(devlog): write Phase 5 retrospective`

### 代码与日志严格分离
**代码改动和 devlog 改动永远不能在同一个 commit 里。**

Phase 完成的标准 commit 序列:
```bash
# 1. 代码完成,验收通过
git add <代码文件>
git commit -m "feat(<模块>): Phase X implementation complete"

# 2. 等用户验收

# 3. 验收通过后写 devlog

# 4. 单独 commit devlog
git add devlog/
git commit -m "docs(devlog): Phase X retrospective"

# 5. 打 tag
git tag phase-X-complete
```

### Commit 前必检
执行 `git status` 并确认:
- `.env` 不在待提交列表
- `output/` 不在待提交列表  
- `.venv/` 不在待提交列表
- 待提交文件类型与 commit message 类型一致(代码不混日志,反之亦然)

异常情况停下来问用户,不要擅自处理。

## 🛡️ 安全红线(永不触碰)

- ❌ 不执行 `git reset --hard` 或 `git push --force`
- ❌ 不执行 `git clean -fd` 或类似删除未追踪文件的命令
- ❌ 不在对话中显示 `.env` 文件的内容或任何 API key
- ❌ 不删除 SPEC.md / PLAN.md / devlog/ 下的任何文件
- ❌ 不修改用户已经手动编辑过的配置文件(除非用户明确要求)

需要执行任何危险操作前,**先描述意图并等用户确认**。

## 📝 开发日志规则

每个 Phase 验收通过后,基于 `devlog/TEMPLATE.md` 写本 Phase 的日志,文件名 `phase-{编号}-{简短主题}.md`。

日志要求:
- **真实**:写出走过的弯路、犯过的错、第一次的失败尝试。不要美化成"一步到位"
- **聚焦决策**:重点记录"为什么这么做",而不仅仅是"做了什么"
- **长度适中**:500-1500 字
- **不改代码**:写日志步骤只能修改 devlog/ 下的文件,不得修改其他任何代码或配置

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

## 🤝 与用户的互动节奏

用户角色: 产品经理 + 验收官,不一定写代码,但所有决策由他做出。

每个 Phase 的标准节奏:
1. 你说: "开始 Phase X,计划 ___,等我开工指令"
2. 用户: "开始" 或 "先调整 ___"
3. 你: 写代码 + 中途按规则 commit + 完成报告
4. 用户验收
5. 你: 写 devlog + commit devlog + 打 tag + 汇报 hash 和 tag
6. 用户: "通过,开始 Phase X+1"

不在节奏内的事(比如新需求、规则变更),先停下来确认。

---

**最后提醒**: 当你不确定该怎么做时,默认选择是 **"停下来问用户"**,而不是 "自己发挥"。
