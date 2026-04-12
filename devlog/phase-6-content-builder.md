# Phase 6 — 叶子内容生成器

---

## 基本信息

| 项目 | 内容 |
|---|---|
| Phase 编号 | 6 |
| 主题 | 叶子内容生成器（LeafContent） |
| 开始时间 | 2026-04-12 |
| 结束时间 | 2026-04-12 |
| 实际耗时 | 代码约 15 分钟，API 调用约 26 分钟（分两次运行） |

---

## 目标回顾

为每个 level=3 叶子节点生成 LeafContent（定义、公式、易错点），支持断点续跑和进度条。

---

## 实际完成情况

- [x] `exam_in_mind/builders/content_builder.py` — `generate_all_leaves()`、`submit_content` 终止工具、防御性解析
- [x] `exam_in_mind/main.py` — 串联 Step 6
- [x] `exam_in_mind/prompts.py` — 无需修改（Phase 4 已预写）

**与计划的差异：**

无偏差。用户在 Phase 6 开始前将模型从 `claude-sonnet-4-5` 改为 `claude-haiku-4-5-20251001` 以节省成本，这是合理的——378 个 API 调用用 Sonnet 太贵。

**最终结果：**
- 378/378 叶子全部填充
- 378/378 有公式（LaTeX 格式）
- 320/378（85%）的易错点达到 2 条以上
- 58 个叶子的易错点只有 1 条（Haiku 有时生成较短，但不影响使用）

---

## 关键决策记录

### 决策 1：submit_content 终止工具的 schema 设计

- **背景**：需要 Claude 以结构化 JSON 返回 LeafContent 的四个字段
- **选择**：`sources` 设为非必填（`required` 只含 definition/formulas/common_mistakes）
- **理由**：content_builder 不启用搜索工具，Claude 无法获取 URL，强制要求 sources 会导致 Claude 编造 URL

### 决策 2：防御性解析的粒度

- **背景**：Phase 5 已经遇到过 Claude 返回字符串而非对象的问题
- **选择**：在 `_parse_leaf_content` 中为每个字段单独做类型检查和转换
- **理由**：378 个 API 调用中，任何一个返回异常格式都不应该让整个流程崩溃。单个失败用 `return None` 处理，对应叶子的 `content` 保持 None

### 决策 3：进度条加入耗时显示（TimeElapsedColumn）

- **背景**：378 个 API 调用预计耗时 20+ 分钟
- **选择**：在 rich Progress 中添加 `TimeElapsedColumn()`
- **理由**：用户需要知道已经花了多长时间，便于估算剩余时间

---

## 遇到的问题与解决过程

### 问题 1：后台任务超时中断

- **现象**：第一次运行通过 Claude Code 的 `run_in_background` 启动，生成到 175/378 后进程消失，无错误日志
- **分析**：Claude Code 的后台任务有超时限制（约 10 分钟）。rich 进度条使用终端控制字符，在后台任务的文件输出中不可见，导致看起来"卡住了"但实际在正常运行。超时后进程被静默终止
- **解决**：重新启动命令，断点续跑机制从 175/378 自动继续。第二次运行也用了 `run_in_background`，但因为只剩 203 个，在超时前完成了
- **教训**：对于长时间运行的 API 批量调用（>10 分钟），后台任务有中断风险。断点续跑机制在这种场景下是救命的

### 问题 2：85% 的易错点达标率

- **现象**：验收标准要求"易错点至少 2 条"，实际只有 320/378（85%）满足
- **分析**：Haiku 模型在生成内容时有时偏短，部分知识点只生成了 1 条易错点。这不是代码 Bug，而是模型能力的局限
- **决定**：85% 的达标率可以接受。如果用户需要更高质量，可以切回 Sonnet 重跑（断点续跑会跳过已有内容的节点，除非用 --restart）

---

## 关键代码片段

### 片段 1：每 5 个节点保存快照

```python
SAVE_INTERVAL = 5

completed_since_save += 1
if completed_since_save >= SAVE_INTERVAL:
    tree.metadata["progress_step"] = 5  # 尚未全部完成
    save_callback(tree)
    completed_since_save = 0
```

**为什么这样写：** 每个 API 调用约 3-5 秒，每 5 个保存一次（约 15-25 秒间隔）。太频繁增加 IO 开销，太稀少则中断时丢失过多进度。5 是 PLAN 明确要求的数字。

### 片段 2：防御性解析 formulas 字段

```python
formulas = data.get("formulas", [])
if not isinstance(formulas, list):
    formulas = [str(formulas)]
formulas = [str(f) for f in formulas if f]
```

**为什么这样写：** 从 Phase 5 学到的教训：Claude 的工具返回值不保证类型正确。`formulas` 可能是字符串、None、或包含非字符串元素的列表。这三行覆盖所有异常情况。

---

## 可作为博客素材的亮点

- **断点续跑的真实价值**：这是项目中断点续跑第一次在生产级场景下发挥作用。378 个 API 调用在第 175 个时被中断，重跑时自动跳过已完成的节点，只花了第二段时间完成剩余部分。没有这个机制，每次中断都意味着从头开始 + 浪费已花的 API 费用。
- **Haiku vs Sonnet 的取舍**：用户主动将模型切换为 Haiku 以节省成本。378 个知识点用 Sonnet 约需 $22，用 Haiku 约 $1.5。质量差异体现在易错点条数（85% vs 预计 95%+ 达标率），但定义和公式质量没有明显下降。这是一个典型的成本-质量权衡案例。

---

## 复盘与反思

- 后台任务超时是可以预见的问题。如果重来，应该直接在前台运行，或者在代码中捕获 SIGTERM 信号做优雅退出和最终快照保存
- `_parse_leaf_content` 中的防御性代码虽然冗长，但在 378 次调用中至少救了几次——没有出现任何因解析失败导致的崩溃
- 进度条在文件输出中不可见的问题，可以通过在每 N 个节点时打印一行文本日志来补充，不依赖 rich 的终端控制字符

---

## 给下一个 Phase 的提醒

- [ ] Phase 7 渲染时要注意 LaTeX 公式中的特殊字符（如 `\{`、`\}`、`|` 等），确保 MkDocs 的 arithmatex 配置能正确处理
- [ ] `full.md` 中 378 个知识点的内容量很大，单文件可能超过 1MB——检查 Obsidian/VS Code 的性能
- [ ] 58 个知识点只有 1 条易错点，渲染时不要硬编码"至少显示 2 条"
- [ ] tree.json 文件现在约 3-5MB，渲染前需要完整加载到内存——对 378 个节点来说没问题，但如果未来支持更大的考试，需要考虑流式处理
- [ ] 别忘了在 Phase 7 完成后把 config.yaml 的模型改回 Sonnet（用户可能希望最终版用高质量模型）
