"""
宏观框架构建器

调用 Claude（启用 Brave Search 工具），查询指定考试的官方考纲，
生成 level=1 的 Unit 节点列表。

主要函数：build_outline()
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from rich.console import Console

from exam_in_mind.config import AppConfig
from exam_in_mind.llm_client import LLMClient
from exam_in_mind.models import ExamTree, KnowledgeNode
from exam_in_mind.prompts import OUTLINE_BUILDER_SYSTEM, build_outline_user_prompt
from exam_in_mind.tools import ALL_TOOLS, dispatch_tool

console = Console()

# ── submit_outline 终止工具定义 ───────────────────────────────────────────────
# Claude 调用此工具提交最终结构化大纲，我们捕获其 input 作为输出

SUBMIT_OUTLINE_TOOL: dict[str, Any] = {
    "name": "submit_outline",
    "description": (
        "提交最终整理好的考试大纲框架。"
        "当你完成搜索和整理后，调用此工具提交所有 Unit 的结构化信息。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "units": {
                "type": "array",
                "description": "所有顶层 Unit 的列表",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Unit 编号，如 '1', '2', '3'",
                        },
                        "title": {
                            "type": "string",
                            "description": "Unit 官方标题",
                        },
                        "summary": {
                            "type": "string",
                            "description": "一句话简介（目标语言）",
                        },
                        "importance": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 5,
                            "description": "考试重要度 1-5",
                        },
                    },
                    "required": ["id", "title", "summary", "importance"],
                },
            }
        },
        "required": ["units"],
    },
}

# outline_builder 可用的工具：search_web（搜索）+ submit_outline（提交结果）
OUTLINE_TOOLS = ALL_TOOLS + [SUBMIT_OUTLINE_TOOL]


def build_outline(
    exam_name: str,
    lang: str,
    cfg: AppConfig,
) -> list[KnowledgeNode]:
    """
    调用 Claude + Brave Search，生成考试的 level=1 Unit 节点列表。

    流程：
        1. 构造 prompt，附带 search_web 和 submit_outline 两个工具
        2. Claude 调用 search_web 搜索官方考纲
        3. Claude 调用 submit_outline 提交结构化结果
        4. 解析结果为 KnowledgeNode 列表

    参数:
        exam_name: 考试名称，如 'AP Calculus BC'
        lang:      输出语言，如 'zh'
        cfg:       AppConfig 配置对象

    返回:
        list[KnowledgeNode]，每个节点 level=1，children 为空
    """
    console.print(f"\n[bold cyan]Step 3: 构建考试大纲框架[/bold cyan]")
    console.print(f"  考试: {exam_name} | 语言: {lang}")

    # 初始化 LLM 客户端
    llm = LLMClient(
        api_key=cfg.anthropic_api_key,
        model=cfg.llm.model,
        max_tokens=cfg.llm.max_tokens,
        temperature=cfg.llm.temperature,
    )

    # 构造 tool dispatcher（需要传入 brave api key）
    def dispatcher(tool_name: str, tool_input: dict) -> str:
        """根据搜索开关决定是否执行 search_web。"""
        if tool_name == "search_web" and not cfg.search.enabled:
            return "（搜索已禁用）"
        # 临时注入 api key 到 brave_search
        if tool_name == "search_web":
            from exam_in_mind import brave_search
            query = tool_input.get("query", "")
            count = tool_input.get("count", cfg.search.results_per_query)
            console.print(f"  [dim]🔍 搜索: {query}[/dim]")
            results = brave_search.search(query, count=count, api_key=cfg.brave_search_api_key)
            formatted = brave_search.format_results_for_llm(results)
            console.print(f"  [dim]   返回 {len(results)} 条结果[/dim]")
            return formatted
        return dispatch_tool(tool_name, tool_input)

    # 构造消息
    user_prompt = build_outline_user_prompt(
        exam_name=exam_name,
        lang=lang,
        count_hint=cfg.tree.level_1_count_hint,
    )
    messages = [{"role": "user", "content": user_prompt}]

    console.print("  [dim]正在调用 Claude（启用搜索）...[/dim]")

    # 运行 tool_use 循环，等待 submit_outline 终止
    _, tool_input = llm.run_tool_loop(
        messages=messages,
        tools=OUTLINE_TOOLS,
        tool_dispatcher=dispatcher,
        system=OUTLINE_BUILDER_SYSTEM,
        terminal_tool="submit_outline",
    )

    if not tool_input or "units" not in tool_input:
        raise RuntimeError("outline_builder: Claude 未调用 submit_outline 或返回格式错误")

    # 解析为 KnowledgeNode 列表
    nodes = _parse_units(tool_input["units"])
    console.print(f"  [green]✓ 生成 {len(nodes)} 个 Unit[/green]")
    for node in nodes:
        console.print(f"    [{node.id}] {node.title} (重要度: {node.importance})")

    return nodes


def _parse_units(units_data: list[dict]) -> list[KnowledgeNode]:
    """
    将 submit_outline 返回的 units 列表解析为 KnowledgeNode 对象。

    参数:
        units_data: Claude 通过 submit_outline 工具提交的 units 列表

    返回:
        list[KnowledgeNode]，level=1，children=[]
    """
    nodes = []
    for i, unit in enumerate(units_data, 1):
        # 如果 Claude 没有提供 id，自动生成
        node_id = str(unit.get("id", str(i)))
        node = KnowledgeNode(
            id=node_id,
            title=unit.get("title", f"Unit {i}"),
            level=1,
            summary=unit.get("summary", ""),
            importance=max(1, min(5, int(unit.get("importance", 3)))),
            children=[],
        )
        nodes.append(node)
    return nodes


def make_exam_tree(
    exam_name: str,
    lang: str,
    root_nodes: list[KnowledgeNode],
    model_name: str,
) -> ExamTree:
    """
    用 outline 结果构造 ExamTree 对象。

    参数:
        exam_name:   考试名称
        lang:        语言
        root_nodes:  level=1 节点列表
        model_name:  使用的模型名（存入 metadata）

    返回:
        ExamTree 对象
    """
    return ExamTree(
        exam_name=exam_name,
        language=lang,
        generated_at=datetime.now(timezone.utc).isoformat(),
        root_nodes=root_nodes,
        metadata={
            "model": model_name,
            "progress_step": 3,
        },
    )
