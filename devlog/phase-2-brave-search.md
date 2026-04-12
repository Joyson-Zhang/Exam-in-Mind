# Phase 2 — Brave Search 模块与工具封装

---

## 基本信息

| 项目 | 内容 |
|---|---|
| Phase 编号 | 2 |
| 主题 | Brave Search 模块 + Claude 工具封装 |
| 开始时间 | 2026-04-11 |
| 结束时间 | 2026-04-11 |
| 实际耗时 | 约 20 分钟 |

---

## 目标回顾

实现 Brave Search API 调用，并封装为 Claude 可调用的 custom tool。

---

## 实际完成情况

- [x] `exam_in_mind/brave_search.py` — `search()`、`_parse_results()`、`format_results_for_llm()`、`__main__` 入口
- [x] `exam_in_mind/tools.py` — `SEARCH_WEB_TOOL` schema、`ALL_TOOLS`、`dispatch_tool()`
- [x] `tests/test_brave_search.py` — 9 个测试，覆盖正常查询、401、429、超时、空 key、解析边界、格式化

**与计划的差异：**

PLAN 要求"至少 2 个测试"，实际写了 9 个。额外覆盖了 429、超时、`_parse_results` 边界和格式化函数，没有超出 SPEC 范围。

---

## 关键决策记录

### 决策 1：HTTP 客户端选用 httpx 还是 requests

- **背景**：需要发起 HTTPS 请求调用 Brave API
- **候选方案**：
  - 方案 A：`requests`（更常见，同步）
  - 方案 B：`httpx`（已在 pyproject.toml 中作为 anthropic SDK 的依赖存在，支持同步/异步）
- **最终选择**：方案 B（httpx）
- **理由**：`httpx` 已是项目依赖树中的包（anthropic SDK 引入），不引入新依赖；且接口与 requests 类似，切换成本为零

### 决策 2：`api_key` 参数的 None vs 空字符串语义

- **背景**：`search()` 函数接受可选的 `api_key` 参数，需要决定 `None` 和 `""` 的行为差异
- **初始写法**：`resolved_key = api_key or _get_api_key()`
- **问题**：`""` 是 falsy，会触发 `_get_api_key()` 回退读取真实配置，导致"无 key"测试实际发起了真实 HTTP 请求
- **修正写法**：`resolved_key = _get_api_key() if api_key is None else (api_key or None)`
- **理由**：`None` = "未指定，从配置读取"；`""` = "明确不传 key，不回退"。语义更精确，测试可控

### 决策 3：tool schema 中工具描述语言

- **背景**：Claude tool 的 `description` 用中文还是英文？
- **候选方案**：
  - 方案 A：英文描述（符合大多数 Anthropic 示例）
  - 方案 B：中文描述（项目面向中文用户）
- **最终选择**：方案 B（中文）
- **理由**：description 是给 Claude 读的 prompt 的一部分，项目整体语境是中文，保持一致。Claude 对中文 tool description 理解没有问题

---

## 遇到的问题与解决过程

### 问题 1：`test_search_returns_empty_without_api_key` 测试失败

- **现象**：传入 `api_key=""` 时，预期返回空列表，实际返回了 5 条真实搜索结果
- **分析**：原代码 `resolved_key = api_key or _get_api_key()` 中，`""` 是 falsy，导致回退调用 `_get_api_key()`，后者从配置文件读取了真实的 Brave API key，进而发起了真实 HTTP 请求
- **解决**：修改为 `resolved_key = _get_api_key() if api_key is None else (api_key or None)`，明确区分 `None`（未指定）和 `""`（明确不传）

这是整个 Phase 中唯一的 Bug，从写完到发现到修复用了不到 2 分钟，但它揭示了一个重要原则：**测试不能依赖外部资源的不可用性**。如果用户没有配置 Brave key，这个测试在未修复前会直接跳过（因为 key 不存在），问题就会被掩盖。

---

## 关键代码片段

### 片段 1：api_key 参数的 None vs 空字符串区分

```python
# api_key=None 表示"未指定，从配置读取"；api_key="" 表示"明确不传 key"
resolved_key = _get_api_key() if api_key is None else (api_key or None)
if not resolved_key:
    console.print("[yellow]警告: 未找到 BRAVE_SEARCH_API_KEY，跳过搜索。[/yellow]")
    return []
```

**为什么这样写：** Python 中 `or` 运算符不区分 `None` 和 `""`，在需要精确控制"默认值回退"逻辑时，三元表达式更安全。

### 片段 2：tool dispatcher 设计

```python
def dispatch_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    if tool_name == "search_web":
        return _run_search_web(tool_input)
    return f"错误：未知工具 '{tool_name}'"
```

**为什么这样写：** 返回字符串而非抛异常，是因为这个返回值会直接作为 `tool_result` 传回 Claude。Claude 收到错误说明后可以自行判断如何继续，比直接崩溃更健壮。Phase 4 集成时，llm_client 会在 tool_use 循环中调用这个函数。

### 片段 3：format_results_for_llm 的输出格式

```python
lines.append(f"[{i}] {item['title']}")
lines.append(f"    URL: {item['url']}")
if item["description"]:
    lines.append(f"    摘要: {item['description']}")
lines.append("")
```

**为什么这样写：** 编号+缩进的格式对 LLM 友好，Claude 可以在引用来源时用 `[1]`、`[2]` 这样的方式指代，便于后续在 `LeafContent.sources` 中记录 URL。

---

## 可作为博客素材的亮点

- **`None` vs `""` 的语义陷阱**：Python 的 `or` 运算符在参数默认值回退场景下容易踩坑。一行代码改动背后是一个值得记录的设计原则：显式优于隐式，尤其在函数签名的可选参数处。
- **测试暴露了"依赖外部不可用"的反模式**：原始测试逻辑隐含了"没有 key 就不会发请求"的假设，但这个假设在有配置文件的环境下不成立。好的测试应该 mock 掉所有外部依赖，而不是依赖外部资源恰好不可用。

---

## 复盘与反思

- 如果重来，会在写 `search()` 函数时就先想清楚 `api_key` 参数的 `None`/`""`/`"real-key"` 三种情况，避免后期改动
- `_get_api_key()` 每次都实例化 `AppConfig` 是个小性能问题，Phase 4 集成时应改为从外部传入 key，而不是在 brave_search 内部读配置

---

## 给下一个 Phase 的提醒

- [ ] `_get_api_key()` 在每次 `search()` 调用时都会重新构建 `AppConfig`，Phase 4 集成时应改为把 key 从 `AppConfig` 传入，避免重复加载 yaml 和 .env
- [ ] Phase 3 的 `cache.py` 中 `get_progress()` 需要明确定义"进度"的判断标准（通过检查哪个字段来确定到第几步），建议在 Phase 3 中与 SPEC 第 5 节的 8 个步骤对齐
- [ ] Brave 免费 tier 限制约 1 QPS，`outline_builder`（Phase 4）若需多次搜索，需在调用之间加适当延迟
