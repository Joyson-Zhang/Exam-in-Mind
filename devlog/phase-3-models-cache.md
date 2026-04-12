# Phase 3 — 数据模型与缓存系统

---

## 基本信息

| 项目 | 内容 |
|---|---|
| Phase 编号 | 3 |
| 主题 | 数据模型（Pydantic）+ JSON 缓存读写 |
| 开始时间 | 2026-04-11 |
| 结束时间 | 2026-04-11 |
| 实际耗时 | 约 20 分钟（全部一次通过，无 Bug） |

---

## 目标回顾

实现知识树的 Pydantic 模型和 JSON 缓存读写。
交付 `models.py`、`cache.py`、`tests/test_models.py`、`tests/test_cache.py`。

---

## 实际完成情况

- [x] `exam_in_mind/models.py` — `LeafContent`、`KnowledgeNode`（含辅助方法）、`ExamTree`
- [x] `exam_in_mind/cache.py` — `save_tree`、`load_tree`、`get_progress`、`get_progress_description`、`backup_tree`
- [x] `tests/test_models.py` — 16 个测试
- [x] `tests/test_cache.py` — 15 个测试，共 31 个全部通过

**与计划的差异：**

SPEC 第 4 节只要求三个模型类，实际在 `KnowledgeNode` 上额外加了三个辅助方法（`is_leaf()`、`has_content()`、`iter_leaves()`）和 `ExamTree` 上的 `all_leaves()`、`count_leaves()`、`count_filled_leaves()`。这些方法在后续 Phase 中频繁需要，集中在模型层实现比在各 builder 里重复写更合理。`cache.py` 比 PLAN 多实现了 `get_progress_description()` 和 `backup_tree()`，后者在 SPEC 第 7 节（断点续跑 restart 分支）中有明确需求，提前实现。

---

## 关键决策记录

### 决策 1：辅助方法放在模型层还是工具函数层

- **背景**：`iter_leaves()`、`count_filled_leaves()` 等操作会在 tree_builder、content_builder、renderers 中反复用到，需要决定放在哪里
- **候选方案**：
  - 方案 A：放在 `models.py` 作为 `KnowledgeNode`/`ExamTree` 的方法
  - 方案 B：写成 `utils.py` 里的独立函数
- **最终选择**：方案 A
- **理由**：这些操作的逻辑完全依赖模型本身的数据，是模型的自然行为而非外部工具。放在模型层符合面向对象封装原则，调用方也更直观（`tree.all_leaves()` 比 `get_all_leaves(tree)` 更清晰）

### 决策 2：`get_progress()` 的步骤编号设计

- **背景**：SPEC 第 5 节定义了 8 个步骤（Step 1-8），但 `cache.py` 只能通过树结构判断，无法感知文件系统（Step 7/8 需要检查 `full.md` 和 `site/` 是否存在）
- **候选方案**：
  - 方案 A：只报告 0/3/4/5/6，Step 7/8 留给 `main.py` 检查文件系统
  - 方案 B：用 `metadata` 字段显式存储当前步骤编号
- **最终选择**：方案 A，但在 docstring 里明确说明局限性
- **理由**：方案 B 需要在每个步骤结束时手动更新 metadata，容易出现"metadata 说已到 Step 6 但树结构不完整"的不一致。方案 A 从树结构本身推断，永远不会与实际数据不一致

### 决策 3：save_tree 的原子写入

- **背景**：如果在写 tree.json 过程中程序崩溃，会得到一个损坏的半写文件，下次启动时 load_tree 会报错
- **候选方案**：
  - 方案 A：直接写目标文件
  - 方案 B：先写 `.tmp` 临时文件，写完后原子替换（`Path.replace()`）
- **最终选择**：方案 B
- **理由**：`Path.replace()` 在同一文件系统上是原子操作（rename syscall），写入中途崩溃只会留下 `.tmp` 文件，原始 `tree.json` 不受影响。这对"断点续跑"功能的可靠性至关重要

---

## 遇到的问题与解决过程

**本 Phase 没有遇到 Bug，所有 31 个测试一次通过。**

有一个需要注意的 Pydantic v2 细节：`KnowledgeNode` 是自引用递归模型（`children: list["KnowledgeNode"]`），在 Pydantic v2 中必须在类定义后显式调用 `KnowledgeNode.model_rebuild()` 才能正确解析前向引用，否则递归字段的验证会失败。这在 SPEC 的示例代码中没有写，但是 Pydantic v2 的必要步骤。

```python
# 让 KnowledgeNode 支持自引用（递归模型）
KnowledgeNode.model_rebuild()
```

---

## 关键代码片段

### 片段 1：原子写入实现

```python
def save_tree(tree: ExamTree, path: Path) -> None:
    tmp_path = path.with_suffix(".tmp")
    try:
        data = tree.model_dump()
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp_path.replace(path)  # 原子替换
    except Exception as e:
        if tmp_path.exists():
            tmp_path.unlink()
        raise RuntimeError(f"保存 tree.json 失败: {e}") from e
```

**为什么这样写：** 断点续跑依赖缓存文件的可靠性。原子替换确保文件要么是旧的完整版，要么是新的完整版，永远不会是损坏的半写状态。

### 片段 2：get_progress 的结构推断逻辑

```python
def get_progress(tree: ExamTree) -> int:
    if not tree.root_nodes:
        return 0
    has_level_2 = any(len(node.children) > 0 for node in tree.root_nodes)
    if not has_level_2:
        return 3
    has_level_3 = any(
        len(child.children) > 0 or child.level == 3
        for node in tree.root_nodes
        for child in node.children
    )
    if not has_level_3:
        return 4
    leaves = tree.all_leaves()
    all_filled = all(leaf.has_content() for leaf in leaves)
    return 6 if all_filled else 5
```

**为什么这样写：** 从树结构本身推断进度，而不是依赖外部状态标记，保证数据一致性。每层检查都是必要的：level_3 的判断需要同时考虑"有子节点"和"自身就是 level=3"两种情况。

### 片段 3：load_tree 的分层错误处理

```python
except json.JSONDecodeError as e:
    console.print(f"[red]错误: tree.json 格式损坏，无法解析 JSON: {e}[/red]")
    console.print("[yellow]提示: 可删除该文件后重新运行，或使用 --restart 参数。[/yellow]")
    return None
except Exception as e:
    console.print(f"[red]错误: 加载 tree.json 失败: {e}[/red]")
    ...
    return None
```

**为什么这样写：** 分开捕获 `json.JSONDecodeError` 和通用 `Exception`，给用户更精准的错误信息。JSON 格式损坏和 Pydantic 校验失败是两种不同问题，用户操作方式也不同。

---

## 可作为博客素材的亮点

- **Pydantic v2 递归模型的 `model_rebuild()` 陷阱**：自引用模型在 Pydantic v2 中需要显式调用 `model_rebuild()`，这是从 v1 迁移时容易踩的坑。SPEC 示例代码没有这一行，实现时需要补充。
- **原子写入的实践**：用 `.tmp` + `Path.replace()` 实现原子写入，是磁盘 IO 健壮性的基础模式，适合在任何需要"断点恢复"的场景中推广。
- **从数据推断状态 vs 存储状态**：`get_progress()` 选择从树结构推断而非读取 metadata 字段，是"单一信息来源"原则的体现——状态不应该被重复存储在两个地方。

---

## 复盘与反思

- 本 Phase 是三个 Phase 里最顺利的，没有遇到 Bug。原因可能是数据模型层的逻辑最纯粹，没有外部依赖（网络、API、文件系统（测试用 tmp_path））
- 如果重来，`get_progress()` 的返回值设计可以考虑用 `Enum` 而不是裸 `int`，更不容易被误用。但考虑到 SPEC 已经用数字描述步骤，保持一致性也合理

---

## 给下一个 Phase 的提醒

- [ ] Phase 4 的 `llm_client.py` 需要实现 tool_use 循环：发送请求 → 收到 tool_use 块 → 调 `dispatch_tool()` → 返回 tool_result → 再次调用 Claude。这个循环需要仔细处理 Anthropic API 的消息格式
- [ ] `outline_builder` 需要 Claude 强制返回 JSON（list[KnowledgeNode] 格式）。建议用 tool_use 模式（定义一个 `submit_outline` 工具）而非依赖 Claude 自由文本输出，这样可以用 Pydantic 校验结果
- [ ] `get_progress()` 目前无法区分"Step 7/8 是否完成"（需要检查文件系统），`main.py` 在 Phase 8 需要补充这部分逻辑
- [ ] Phase 4 的 `main.py` 集成部分：outline 完成后需要调用 `save_tree()`，路径由 `exam_name` 转成 slug（空格→下划线，全小写）确定
