# Phase 5 — 递归分解器

---

## 基本信息

| 项目 | 内容 |
|---|---|
| Phase 编号 | 5 |
| 主题 | 递归分解器（level=1 → level=2 → level=3） |
| 开始时间 | 2026-04-11 |
| 结束时间 | 2026-04-11 |
| 实际耗时 | 约 45 分钟（含两次运行 + 调试两个 Bug） |

---

## 目标回顾

把 level=1 的树扩展到 level=3（章 → 节 → 知识点），每完成一个父节点保存快照，支持断点续跑。

---

## 实际完成情况

- [x] `exam_in_mind/builders/tree_builder.py` — `expand_to_level_2()`、`expand_to_level_3()`、`submit_nodes` 工具、rich 进度条
- [x] `exam_in_mind/main.py` — 串联 Step 4/Step 5，含断点续跑
- [x] `exam_in_mind/prompts.py` — 无需修改（Phase 4 已预写）

**与计划的差异：**

`prompts.py` 中的 `EXPAND_TO_LEVEL_2_PROMPT` 和 `EXPAND_TO_LEVEL_3_PROMPT` 在 Phase 4 已提前写好，本 Phase 直接使用。无偏差。

最终结果：10 Units → 68 Sections → 378 知识点。

---

## 关键决策记录

### 决策 1：断点续跑的判定方式

- **背景**：需要在 Ctrl+C 后重跑时跳过已完成的节点
- **候选方案**：
  - 方案 A：在 metadata 里记录"最后处理的节点 id"
  - 方案 B：直接检查节点的 `children` 是否为空——空表示未展开
- **最终选择**：方案 B
- **理由**：与 Phase 3 cache.py 的 `get_progress()` 设计一致——从数据本身推断状态而非维护外部标记。更简单、不可能出现"标记说完了但 children 为空"的不一致

### 决策 2：save_callback 回调模式

- **背景**：tree_builder 需要在每个节点完成后保存快照，但不应该知道文件路径
- **候选方案**：
  - 方案 A：把 tree_path 传给 tree_builder，让它自己调 save_tree
  - 方案 B：接受一个 `save_callback: Callable[[ExamTree], None]` 回调
- **最终选择**：方案 B
- **理由**：tree_builder 只管构建逻辑，保存策略由 main.py 决定。职责分离更清晰，也方便测试（传入空回调即可）

---

## 遇到的问题与解决过程

### 问题 1：`_parse_nodes` 中 Claude 返回字符串而非对象

- **现象**：Step 5 在展开 Section [1.6] "Types of Discontinuities" 时崩溃，报 `'str' object has no attribute 'get'`
- **分析**：`tool_input["nodes"]` 中的某些项是字符串（如 `"1.6.1: Point Discontinuity"`）而非期望的 `{"id": "1.6.1", ...}` 对象。Anthropic tool use 的 `input_schema` 对数组元素的类型校验不是严格的——schema 说 items 应为 object，但 API 有时仍允许 string 通过
- **解决**：在 `_parse_nodes` 中加入 `if not isinstance(item, dict): continue`，跳过非 dict 项并打印警告。378 个知识点中约有 3 个被跳过（381→378），影响可忽略

**这个 Bug 揭示了一个重要教训：不要假设 LLM 工具调用的返回值一定符合 schema，防御性解析是必须的。**

### 问题 2：断点续跑条件写错，导致部分完成的 Step 5 被跳过

- **现象**：修复问题 1 后重跑，程序显示"Step 5 已完成，跳过"——但实际上 68 个 Section 中只有 6 个被展开
- **分析**：`main.py` 中写的是 `if current_step < 5`，而 `get_progress()` 在发现任何 level=3 节点时就返回 5（即使只有部分 Section 被展开了）。所以 `current_step == 5` → `5 < 5 == False` → 跳过
- **解决**：将条件改为 `if current_step < 6`（只有所有叶子都填充了 content 才认为 Step 5 完全完成）。`expand_to_level_3` 内部的 `pending` 列表会自动跳过已展开节点，实现真正的断点续跑
- **根本原因**：`get_progress()` 返回的是"最新到达的 step"，不是"完全完成的 step"。Phase 3 设计 `get_progress` 时没有充分考虑部分完成的情况。这是跨 Phase 接口设计的典型问题

---

## 关键代码片段

### 片段 1：断点续跑的 pending 过滤

```python
# 找出尚未展开的 level=2 节点
all_sections = [
    (unit, section)
    for unit in tree.root_nodes
    for section in unit.children
]
pending = [(u, s) for u, s in all_sections if len(s.children) == 0]
already_done = len(all_sections) - len(pending)
```

**为什么这样写：** 通过 `len(s.children) == 0` 直接从数据推断未完成的节点，不需要额外的进度标记。重跑时自动跳过已有子节点的 Section。

### 片段 2：main.py 中修正后的跳过条件

```python
# Step 5：current_step < 6 才需要运行（expand 内部会跳过已展开节点）
# 如果 current_step == 5 说明 Step 5 只完成了一部分，仍需继续
current_step = get_progress(tree)
if current_step < 6:
    tree = expand_to_level_3(tree, cfg, save_snapshot)
```

**为什么这样写：** `get_progress()` 返回的是"触达"过的最高步骤，不是"完全完成"的步骤。所以 Step N 的跳过条件应该是 `< N+1`（下一步完全完成才说明本步已完全完成），再由 expand 函数内部的 pending 过滤来处理部分完成的情况。

---

## 可作为博客素材的亮点

- **LLM tool use 的 schema 不是铁律**：Anthropic 的 tool use input_schema 对 array items 的类型校验并非 100% 严格。Claude 偶尔会在 `"type": "object"` 的 array 中返回字符串。所有消费 LLM 工具返回值的代码都应该做防御性类型检查。
- **"进度"的语义歧义**：`get_progress()` 返回 5 可能意味着"Step 5 刚开始"或"Step 5 已完成"。这种歧义在单步骤内无影响，但在断点续跑的跳过逻辑中会导致严重 Bug。设计进度系统时应明确区分"进入"和"完成"两种语义。
- **68 个 Section 的断点续跑实测**：第一次运行展开了 66 个，崩溃后第二次只处理了剩余 2 个——这正是断点续跑的设计目标。单次 API 调用的失败不应该浪费之前所有的工作。

---

## 复盘与反思

- 断点续跑的条件本应在 Phase 3 设计 `get_progress()` 时就考虑清楚。如果当时定义了"进入"和"完成"两个状态，Phase 5 的 Bug 就不会出现
- `_parse_nodes` 的防御性检查应该从一开始就有，而不是等崩溃了再补。教训：凡是消费 LLM 输出的地方，类型检查是必须的
- Step 4（68 个 Section）的展开很顺利，一次通过。Step 5 的问题出在 Claude 对更细粒度节点（知识点）的输出格式不如宏观层面稳定

---

## 给下一个 Phase 的提醒

- [ ] Phase 6 的 content_builder 会调用 378 次 Claude API，耗时和成本都是大头。建议实现"每完成 5 个保存一次快照"（PLAN 要求）
- [ ] content_builder 的 `submit_content` 工具返回的 `formulas` 字段是 LaTeX 列表，同样需要防御性检查（可能返回非列表）
- [ ] `_parse_nodes` 跳过非 dict 项的逻辑目前只打印警告，后续可以考虑在 Phase 8 时统计被跳过的总数并在最终报告中提醒用户
- [ ] 注意成本：378 个知识点 × 每次约 4096 token 输出 ≈ 1.5M output tokens，用 Claude Sonnet 约 $22.5。可以考虑先用 Haiku 测试
