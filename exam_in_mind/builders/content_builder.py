"""
叶子内容生成器

遍历知识树中所有 level=3 叶子节点，调用 Claude 为每个节点生成 LeafContent
（定义、公式、易错点）。

特性：
    - 强制 JSON 输出（通过 submit_content 终止工具）
    - 每完成 5 个节点保存一次快照（断点续跑）
    - 跳过已有 content 的节点（断点续跑）
    - rich 进度条实时显示 X/Y

主要函数：generate_all_leaves()
"""

from __future__ import annotations

import ast
import json
import warnings
from typing import Any, Callable

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from exam_in_mind.config import AppConfig
from exam_in_mind.llm_client import LLMClient
from exam_in_mind.models import ExamTree, KnowledgeNode, LeafContent
from exam_in_mind.prompts import CONTENT_BUILDER_SYSTEM, build_leaf_content_prompt

console = Console()

# 每完成多少个节点保存一次快照
SAVE_INTERVAL = 5

# ── submit_content 终止工具定义 ───────────────────────────────────────────────

SUBMIT_CONTENT_TOOL: dict[str, Any] = {
    "name": "submit_content",
    "description": (
        "提交知识点的详细学习内容。"
        "包含定义、核心公式、易错点等结构化信息。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "definition": {
                "type": "string",
                "description": "知识点的完整定义，可包含 LaTeX 公式（用 $...$ 包裹）",
            },
            "formulas": {
                "type": "array",
                "description": "核心公式或定理列表，每条都是 LaTeX 字符串",
                "items": {"type": "string"},
            },
            "common_mistakes": {
                "type": "array",
                "description": "学生常见的 2-4 个错误或易混淆点",
                "items": {"type": "string"},
            },
            "sources": {
                "type": "array",
                "description": "引用来源 URL 列表（可选，如无来源可留空数组）",
                "items": {"type": "string"},
            },
        },
        "required": ["definition", "formulas", "common_mistakes"],
    },
}

CONTENT_TOOLS = [SUBMIT_CONTENT_TOOL]


def generate_all_leaves(
    tree: ExamTree,
    cfg: AppConfig,
    save_callback: Callable[[ExamTree], None],
) -> ExamTree:
    """
    为树中所有未填充的 level=3 叶子节点生成 LeafContent。

    跳过已有 content 的节点（断点续跑）。
    每完成 SAVE_INTERVAL 个节点调用 save_callback 保存快照。

    参数:
        tree:          当前 ExamTree（level=3 节点已存在）
        cfg:           AppConfig 配置对象
        save_callback: 保存快照的回调函数

    返回:
        更新后的 ExamTree（原地修改 + 返回同一对象）
    """
    console.print(f"\n[bold cyan]Step 6: 生成叶子内容[/bold cyan]")

    # 收集所有叶子和它们的路径信息
    leaf_infos = _collect_leaf_infos(tree)
    total = len(leaf_infos)

    # 过滤出未填充的叶子
    pending = [(node, path) for node, path, filled in leaf_infos if not filled]
    already_done = total - len(pending)

    if already_done > 0:
        console.print(f"  [dim]跳过 {already_done} 个已生成节点，继续处理剩余 {len(pending)} 个[/dim]")

    if not pending:
        console.print("  [dim]所有叶子内容已生成，跳过 Step 6[/dim]")
        return tree

    llm = LLMClient(
        api_key=cfg.anthropic_api_key,
        model=cfg.llm.model,
        max_tokens=cfg.llm.max_tokens,
        temperature=cfg.llm.temperature,
    )

    completed_since_save = 0

    with _make_progress() as progress:
        task = progress.add_task(
            f"生成叶子内容 {already_done}/{total}",
            total=len(pending),
        )

        for i, (leaf, parent_path) in enumerate(pending, 1):
            content = _generate_leaf_content(
                llm=llm,
                leaf=leaf,
                parent_path=parent_path,
                lang=tree.language,
            )
            if content:
                leaf.content = content

            completed_since_save += 1
            current_done = already_done + i

            progress.update(
                task,
                advance=1,
                description=f"生成叶子内容 {current_done}/{total}",
            )

            # 每 SAVE_INTERVAL 个节点保存一次快照
            if completed_since_save >= SAVE_INTERVAL:
                tree.metadata["progress_step"] = 5  # 尚未全部完成
                save_callback(tree)
                completed_since_save = 0

    # 最终保存
    tree.metadata["progress_step"] = 6
    save_callback(tree)

    filled = tree.count_filled_leaves()
    console.print(f"  [green]✓ 已生成 {filled}/{total} 个知识点的内容[/green]")
    return tree


# ── 内部辅助函数 ──────────────────────────────────────────────────────────────

def _collect_leaf_infos(
    tree: ExamTree,
) -> list[tuple[KnowledgeNode, str, bool]]:
    """
    收集所有叶子节点及其父路径信息。

    返回:
        list[(节点, 父路径字符串, 是否已填充content)]
        父路径示例: "Unit 1: Limits > 1.2 Continuity"
    """
    infos = []
    for unit in tree.root_nodes:
        for section in unit.children:
            parent_path = f"{unit.title} > {section.title}"
            for leaf in section.children:
                infos.append((leaf, parent_path, leaf.has_content()))
    return infos


def _generate_leaf_content(
    llm: LLMClient,
    leaf: KnowledgeNode,
    parent_path: str,
    lang: str,
) -> LeafContent | None:
    """
    调用 Claude 为单个叶子节点生成 LeafContent。

    参数:
        llm:         LLMClient 实例
        leaf:        目标叶子节点
        parent_path: 父节点路径字符串
        lang:        输出语言

    返回:
        LeafContent 对象，或 None（生成失败时）
    """
    user_prompt = build_leaf_content_prompt(
        node_title=leaf.title,
        node_summary=leaf.summary,
        node_id=leaf.id,
        parent_path=parent_path,
        lang=lang,
    )

    messages = [{"role": "user", "content": user_prompt}]

    try:
        _, tool_input = llm.run_tool_loop(
            messages=messages,
            tools=CONTENT_TOOLS,
            tool_dispatcher=_noop_dispatcher,
            system=CONTENT_BUILDER_SYSTEM,
            terminal_tool="submit_content",
        )
    except Exception as e:
        console.print(f"\n  [red]错误: [{leaf.id}] {leaf.title} 生成失败: {e}[/red]")
        return None

    if not tool_input:
        console.print(f"\n  [yellow]警告: [{leaf.id}] {leaf.title} 未返回 submit_content[/yellow]")
        return None

    return _parse_leaf_content(tool_input, leaf.id)


def _parse_leaf_content(data: dict[str, Any], node_id: str) -> LeafContent | None:
    """
    解析 submit_content 返回的数据为 LeafContent 对象。

    参数:
        data:    submit_content 的 tool_input
        node_id: 节点 id（用于错误日志）

    返回:
        LeafContent 对象，或 None（解析失败时）
    """
    try:
        definition = data.get("definition", "")
        if not definition:
            console.print(f"\n  [yellow]警告: [{node_id}] definition 为空[/yellow]")
            return None

        # 防御性解析：formulas 和 common_mistakes 可能不是列表
        formulas = data.get("formulas", [])
        if not isinstance(formulas, list):
            formulas = [str(formulas)]
        # 展平：Claude 有时将整个数组序列化成一个字符串（以 '[' 开头），需要尝试 JSON 解析
        formulas = _flatten_formula_list(formulas)
        # 过滤非字符串项
        formulas = [str(f) for f in formulas if f]

        common_mistakes = data.get("common_mistakes", [])
        if not isinstance(common_mistakes, list):
            common_mistakes = [str(common_mistakes)]
        common_mistakes = [str(m) for m in common_mistakes if m]

        sources = data.get("sources", [])
        if not isinstance(sources, list):
            sources = [str(sources)]
        sources = [str(s) for s in sources if s]

        return LeafContent(
            definition=str(definition),
            formulas=formulas,
            common_mistakes=common_mistakes,
            sources=sources,
        )
    except Exception as e:
        console.print(f"\n  [yellow]警告: [{node_id}] LeafContent 解析失败: {e}[/yellow]")
        return None


def _flatten_formula_list(formulas: list) -> list[str]:
    """
    展平 formulas 列表中被错误序列化为 JSON 数组字符串的元素。

    Claude 有时会把整个公式数组作为一个字符串返回，如:
        ['["$x^2$", "$y^2$"]']
    需要解析为:
        ['$x^2$', '$y^2$']

    LaTeX 公式中的反斜杠（如 \\frac）在 JSON 中是无效转义，
    因此 json.loads 可能失败，此时回退到 ast.literal_eval。

    参数:
        formulas: 原始 formulas 列表

    返回:
        展平后的字符串列表
    """
    result = []
    for item in formulas:
        if not isinstance(item, str):
            result.append(str(item))
            continue

        stripped = item.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            # 尝试解析为 JSON 数组
            parsed = None
            try:
                parsed = json.loads(stripped)
            except (json.JSONDecodeError, ValueError):
                # LaTeX 转义导致 JSON 解析失败，回退到 ast.literal_eval
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        parsed = ast.literal_eval(stripped)
                except (ValueError, SyntaxError):
                    pass

            if isinstance(parsed, list):
                result.extend(str(f) for f in parsed if f)
                continue

        result.append(item)

    return result


def _noop_dispatcher(tool_name: str, tool_input: dict[str, Any]) -> str:
    """空 dispatcher：content_builder 阶段不使用额外工具。"""
    return f"（工具 '{tool_name}' 在此阶段不可用）"


def _make_progress() -> Progress:
    """构造带耗时的 rich 进度条。"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )
