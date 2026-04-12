"""
Claude 自定义工具定义模块

将 Brave Search 包装为 Claude 可调用的 custom tool（search_web）。
包含：工具 schema 定义、tool dispatcher（接收 tool_use 块 → 执行 → 返回 tool_result）。
"""

from __future__ import annotations

from typing import Any

from rich.console import Console

from exam_in_mind import brave_search

console = Console()

# ── 工具 Schema 定义 ──────────────────────────────────────────────────────────
# 符合 Anthropic tool use 规范：
# https://docs.anthropic.com/en/docs/tool-use

SEARCH_WEB_TOOL: dict[str, Any] = {
    "name": "search_web",
    "description": (
        "使用 Brave Search 搜索互联网，获取最新的网页内容。"
        "适用于查询考试官方考纲、最新课程标准、教材大纲等信息。"
        "返回包含标题、URL 和摘要的搜索结果列表。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词，建议使用英文以获得更准确的结果",
            },
            "count": {
                "type": "integer",
                "description": "返回结果数量，默认 5，最大 20",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}

# 所有可用工具的列表（供 llm_client 直接传给 Anthropic API）
ALL_TOOLS: list[dict[str, Any]] = [SEARCH_WEB_TOOL]


# ── Tool Dispatcher ───────────────────────────────────────────────────────────

def dispatch_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    """
    接收 Claude 返回的 tool_use 请求，执行对应工具，返回结果字符串。

    参数:
        tool_name:  Claude 请求调用的工具名称（如 "search_web"）
        tool_input: Claude 传入的工具参数 dict

    返回:
        工具执行结果的字符串，将作为 tool_result 回传给 Claude。
        若工具名未知，返回错误说明字符串（不抛出异常）。
    """
    if tool_name == "search_web":
        return _run_search_web(tool_input)

    # 未知工具：返回说明而不是崩溃
    return f"错误：未知工具 '{tool_name}'"


def _run_search_web(tool_input: dict[str, Any]) -> str:
    """
    执行 search_web 工具：调用 Brave Search 并将结果格式化为文本。

    参数:
        tool_input: 包含 query（必填）和 count（可选）的 dict

    返回:
        格式化后的搜索结果文本，供 Claude 阅读
    """
    query = tool_input.get("query", "")
    count = tool_input.get("count", 5)

    if not query:
        return "错误：search_web 需要提供 query 参数"

    console.print(f"  [dim]🔍 搜索: {query}[/dim]")
    results = brave_search.search(query, count=count)
    formatted = brave_search.format_results_for_llm(results)

    console.print(f"  [dim]   返回 {len(results)} 条结果[/dim]")
    return formatted
