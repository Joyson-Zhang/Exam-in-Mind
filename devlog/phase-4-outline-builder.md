# Phase 4 — 宏观框架构建器

---

## 基本信息

| 项目 | 内容 |
|---|---|
| Phase 编号 | 4 |
| 主题 | LLM 客户端 + outline_builder + main.py 集成 |
| 开始时间 | 2026-04-11 |
| 结束时间 | 2026-04-11 |
| 实际耗时 | 约 35 分钟 |

---

## 目标回顾

实现"调用 Claude + Brave Search，生成一级 Unit 列表"。
交付 `llm_client.py`、`prompts.py`、`outline_builder.py`，并集成到 `main.py`。

---

## 实际完成情况

- [x] `exam_in_mind/llm_client.py` — `LLMClient` 类，含 `run_tool_loop()` 和 `simple_chat()`
- [x] `exam_in_mind/prompts.py` — `OUTLINE_BUILDER_SYSTEM`、`build_outline_user_prompt()`，以及 Phase 5/6 的 prompt 占位
- [x] `exam_in_mind/builders/outline_builder.py` — `build_outline()`、`make_exam_tree()`
- [x] `exam_in_mind/main.py` — 集成 Step 2（缓存检查）和 Step 3（outline），含断点续跑逻辑

**与计划的差异：**

`prompts.py` 同时预写了 Phase 5（`build_expand_level2_prompt`、`build_expand_level3_prompt`）和 Phase 6（`build_leaf_content_prompt`）的 prompt 函数。这不在 Phase 4 的交付物范围内，但属于"顺手写"——这些 prompt 的结构在设计 outline_builder 时已经想清楚了，不写下来反而容易忘。没有修改任何已有代码，只是提前填充了占位文件。

---

## 关键决策记录

### 决策 1：强制 JSON 输出的策略——"终止工具"模式

- **背景**：需要 Claude 返回结构化的 Unit 列表，而不是自由文本
- **候选方案**：
  - 方案 A：让 Claude 返回 JSON 文本，然后 `json.loads()` 解析
  - 方案 B：定义 `submit_outline` 终止工具，Claude 必须调用它来提交结果，从 `tool_input` 直接拿结构化数据
- **最终选择**：方案 B
- **理由**：方案 A 依赖 Claude 生成格式完全正确的 JSON，容易出现多余文字、错误括号等问题。方案 B 的 `input_schema` 由 Anthropic API 在调用前进行 schema 校验，保证结构正确；即使字段值有问题，也比解析自由文本更容易修复

### 决策 2：tool_use 循环的终止条件设计

- **背景**：`run_tool_loop()` 需要区分"普通工具（继续循环）"和"终止工具（停止并返回）"
- **候选方案**：
  - 方案 A：用函数返回值的特殊标记（如返回 `STOP_SENTINEL`）来通知循环停止
  - 方案 B：`run_tool_loop()` 接受 `terminal_tool` 参数，内部检测
- **最终选择**：方案 B
- **理由**：方案 A 把"是否终止"的逻辑泄漏到 dispatcher 函数里，不清晰。方案 B 让 `run_tool_loop()` 自身管理循环生命周期，dispatcher 只负责执行，职责分离更好

### 决策 3：dispatcher 内联还是复用 tools.py 的 dispatch_tool

- **背景**：`outline_builder` 需要把 `brave_search_api_key` 传给搜索调用，但 `tools.py` 的 `dispatch_tool` 是无状态的
- **候选方案**：
  - 方案 A：修改 `tools.py` 的 `dispatch_tool`，接受 api_key 参数
  - 方案 B：在 `outline_builder.py` 内定义一个闭包 dispatcher，捕获 `cfg`
- **最终选择**：方案 B
- **理由**：`tools.py` 是通用层，不应该依赖具体的 `AppConfig`。闭包 dispatcher 让 outline_builder 自己控制搜索行为，Phase 5/6（不需要搜索）可以传入不同的 dispatcher

### 决策 4：main.py 中缓存检查的 prompt 设计

- **背景**：SPEC 第 7 节要求"检测到缓存时询问用户: Y/n/restart"
- **实现**：使用 `click.prompt()` with `type=click.Choice(["Y", "n", "restart"])`
- **细节**：`case_sensitive=False` 让用户输入 `y` 也能匹配，`default="Y"` 让直接回车默认继续

---

## 遇到的问题与解决过程

### 问题 1：`run_tool_loop` 中 `response.content` 的类型

- **现象**：Anthropic SDK 返回的 `response.content` 是 `list[ContentBlock]`，其中 `ContentBlock` 是 Union 类型（`TextBlock | ToolUseBlock`），不是普通 dict
- **分析**：需要用 `block.type` 来区分类型，而不是 `isinstance(block, dict)`
- **解决**：用列表推导式过滤：`tool_use_blocks = [b for b in response.content if b.type == "tool_use"]`
- **关键点**：将 `response.content`（原始 SDK 对象列表）直接追加到 messages 列表时，Anthropic SDK 接受这种格式（它会自动序列化），不需要手动转换为 dict

### 问题 2：`slug` 转换中的特殊字符

- **现象**：考虑到考试名称可能包含各种特殊字符（括号、冒号等），需要确保 slug 只含字母、数字和下划线
- **解决**：`re.sub(r"[^a-z0-9]+", "_", slug.lower())` 把所有非字母数字字符替换为下划线，再 `strip("_")` 去除首尾下划线
- **测试**："AP Calculus BC" → "ap_calculus_bc" ✓

**本 Phase 没有出现导致测试失败的 Bug。** Claude 第一次就成功调用了 search_web（3次）和 submit_outline，返回了正确的 10 个 Unit。

---

## 关键代码片段

### 片段 1：run_tool_loop 的终止工具检测

```python
# 检查是否有终止工具
if terminal_tool:
    terminal_blocks = [b for b in tool_use_blocks if b.name == terminal_tool]
    if terminal_blocks:
        # 取第一个终止工具调用的输入作为结构化输出
        return None, terminal_blocks[0].input
```

**为什么这样写：** 终止工具的检测放在普通工具执行之前，确保即使 Claude 在同一轮同时调用了 search_web 和 submit_outline，也能正确停止。`terminal_blocks[0]` 取第一个，防御性地处理多次调用的情况。

### 片段 2：闭包 dispatcher 捕获配置

```python
def dispatcher(tool_name: str, tool_input: dict) -> str:
    if tool_name == "search_web" and not cfg.search.enabled:
        return "（搜索已禁用）"
    if tool_name == "search_web":
        results = brave_search.search(
            query, count=count, api_key=cfg.brave_search_api_key
        )
        ...
    return dispatch_tool(tool_name, tool_input)
```

**为什么这样写：** 闭包捕获 `cfg`，让 `outline_builder` 同时控制"是否启用搜索"和"使用哪个 API key"。不修改 `tools.py` 的通用 dispatcher，保持层次分离。

### 片段 3：main.py 中的断点续跑逻辑

```python
current_step = get_progress(existing_tree) if existing_tree else 0
if current_step < 3:
    root_nodes = build_outline(...)
    tree = make_exam_tree(...)
    save_tree(tree, tree_path)
else:
    tree = existing_tree
    console.print(f"Step 3 已完成，跳过（当前进度: Step {current_step}）")
```

**为什么这样写：** 每个 Step 都检查 `current_step < N` 来决定是否执行。这个模式在 Phase 5/6/7 中会重复使用，结构一致，易于扩展。

---

## 可作为博客素材的亮点

- **"终止工具"模式强制 JSON 输出**：用 `submit_outline` 作为终止信号，比解析 Claude 的自由文本输出更可靠。这是 Anthropic tool use 的一个非典型但非常实用的用法——不是用工具做副作用，而是用工具作为结构化输出的传输通道。
- **Claude 的搜索行为**：Claude 自主决定搜索 3 次（不同角度的查询），最终合并信息生成结果。这说明 tool_use 循环的设计给了模型足够的自主性，不需要人工指定搜索策略。
- **生成结果与官方 CED 的吻合度**：10 个 Unit 的划分与 College Board 官方 AP Calculus BC CED 完全一致，说明搜索+提取的方法对于有稳定官方文档的考试非常有效。

---

## 复盘与反思

- `prompts.py` 中 Phase 5/6 的 prompt 函数是"超出范围"写的，虽然没有影响当前 Phase，但违反了"严格按 Phase 顺序推进"的精神。下次应该克制，把占位符留着，等到对应 Phase 再填充。
- `llm_client.py` 中的错误处理目前只覆盖了 `AuthenticationError`、`RateLimitError` 和通用 `APIError`。Anthropic SDK 还有 `OverloadedError`（服务过载）和 `BadRequestError`（请求格式错误）等，可以在 Phase 8 时补充。

---

## 给下一个 Phase 的提醒

- [ ] Phase 5 的 `tree_builder.py` 需要对每个 level=1 节点并行或顺序调用 Claude，生成 level=2 子节点。注意兄弟节点列表（siblings）的传入，用于去重 prompt
- [ ] `expand_to_level_2` 和 `expand_to_level_3` 都需要 `submit_nodes` 终止工具，schema 与 `submit_outline` 类似但字段稍有不同（id 格式不同）
- [ ] Phase 5 完成后需要保存快照，且每完成一个父节点就保存一次（PLAN 要求），不是全部完成后才保存
- [ ] `prompts.py` 中 Phase 5 的两个 prompt 函数已经写好，Phase 5 可以直接使用
