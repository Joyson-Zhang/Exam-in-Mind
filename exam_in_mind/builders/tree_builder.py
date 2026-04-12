"""
递归分解器

将 level=1 的 Unit 节点逐层扩展为 level=2（Section）和 level=3（知识点）。

主要函数：
    expand_to_level_2(tree, cfg, save_callback) -> ExamTree
    expand_to_level_3(tree, cfg, save_callback) -> ExamTree

断点续跑逻辑：
    - 已有子节点的节点（len(children) > 0）视为已展开，直接跳过
    - 每完成一个父节点立即调用 save_callback 保存快照
"""

from __future__ import annotations

from typing import Any, Callable

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from exam_in_mind.config import AppConfig
from exam_in_mind.llm_client import LLMClient
from exam_in_mind.models import ExamTree, KnowledgeNode
from exam_in_mind.prompts import (
    TREE_BUILDER_SYSTEM,
    build_expand_level2_prompt,
    build_expand_level3_prompt,
)

console = Console()

# ── submit_nodes 终止工具定义 ─────────────────────────────────────────────────
# Claude 调用此工具提交分解好的子节点列表

SUBMIT_NODES_TOOL: dict[str, Any] = {
    "name": "submit_nodes",
    "description": (
        "提交分解好的子节点列表。"
        "当你完成对当前节点的分解后，调用此工具提交所有子节点的结构化信息。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "nodes": {
                "type": "array",
                "description": "子节点列表",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "节点编号，如 '1.1' 或 '1.1.2'",
                        },
                        "title": {
                            "type": "string",
                            "description": "节点标题",
                        },
                        "summary": {
                            "type": "string",
                            "description": "一句话简介（目标语言）",
                        },
                        "importance": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 5,
                            "description": "重要度 1-5",
                        },
                    },
                    "required": ["id", "title", "summary", "importance"],
                },
            }
        },
        "required": ["nodes"],
    },
}

TREE_BUILDER_TOOLS = [SUBMIT_NODES_TOOL]


# ── 公开函数 ──────────────────────────────────────────────────────────────────

def expand_to_level_2(
    tree: ExamTree,
    cfg: AppConfig,
    save_callback: Callable[[ExamTree], None],
) -> ExamTree:
    """
    将树中所有 level=1 节点扩展为带 level=2 子节点的结构。

    跳过已有子节点的节点（断点续跑）。
    每完成一个节点立即调用 save_callback 保存快照。

    参数:
        tree:          当前 ExamTree（level=1 节点已存在）
        cfg:           AppConfig 配置对象
        save_callback: 每完成一个节点后调用，传入更新后的 tree

    返回:
        更新后的 ExamTree（原地修改 + 返回同一对象）
    """
    console.print(f"\n[bold cyan]Step 4: 扩展至 level=2（Section）[/bold cyan]")

    # 找出尚未展开的 level=1 节点
    pending = [n for n in tree.root_nodes if len(n.children) == 0]
    already_done = len(tree.root_nodes) - len(pending)

    if already_done > 0:
        console.print(f"  [dim]跳过 {already_done} 个已展开节点，继续处理剩余 {len(pending)} 个[/dim]")

    if not pending:
        console.print("  [dim]所有节点已展开，跳过 Step 4[/dim]")
        return tree

    llm = _make_llm(cfg)
    # 所有 level=1 节点的标题（用于去重 prompt）
    all_unit_titles = [n.title for n in tree.root_nodes]

    with _make_progress() as progress:
        task = progress.add_task(
            f"展开 Section...", total=len(pending)
        )
        for node in pending:
            siblings = [t for t in all_unit_titles if t != node.title]
            children = _expand_node(
                llm=llm,
                parent=node,
                siblings=siblings,
                target_level=2,
                lang=tree.language,
                count_hint=cfg.tree.level_2_count_hint,
            )
            node.children = children
            tree.metadata["progress_step"] = 4
            save_callback(tree)
            progress.advance(task)
            progress.update(
                task,
                description=f"展开 Section... [{node.id}] {node.title[:30]}",
            )

    total_sections = sum(len(n.children) for n in tree.root_nodes)
    console.print(f"  [green]✓ 共生成 {total_sections} 个 Section[/green]")
    return tree


def expand_to_level_3(
    tree: ExamTree,
    cfg: AppConfig,
    save_callback: Callable[[ExamTree], None],
) -> ExamTree:
    """
    将树中所有 level=2 节点扩展为带 level=3 子节点（知识点）的结构。

    跳过已有子节点的节点（断点续跑）。
    每完成一个节点立即调用 save_callback 保存快照。

    参数:
        tree:          当前 ExamTree（level=2 节点已存在）
        cfg:           AppConfig 配置对象
        save_callback: 每完成一个节点后调用

    返回:
        更新后的 ExamTree
    """
    console.print(f"\n[bold cyan]Step 5: 扩展至 level=3（知识点）[/bold cyan]")

    # 收集所有 level=2 节点，找出尚未展开的
    all_sections = [
        (unit, section)
        for unit in tree.root_nodes
        for section in unit.children
    ]
    pending = [(u, s) for u, s in all_sections if len(s.children) == 0]
    already_done = len(all_sections) - len(pending)

    if already_done > 0:
        console.print(f"  [dim]跳过 {already_done} 个已展开节点，继续处理剩余 {len(pending)} 个[/dim]")

    if not pending:
        console.print("  [dim]所有节点已展开，跳过 Step 5[/dim]")
        return tree

    llm = _make_llm(cfg)

    with _make_progress() as progress:
        task = progress.add_task(
            "展开知识点...", total=len(pending)
        )
        for unit, section in pending:
            # 同级 Section 标题（同一 Unit 下的其他 section）
            siblings = [
                s.title for s in unit.children if s.id != section.id
            ]
            children = _expand_node(
                llm=llm,
                parent=section,
                siblings=siblings,
                target_level=3,
                lang=tree.language,
                count_hint=cfg.tree.level_3_count_hint,
            )
            section.children = children
            tree.metadata["progress_step"] = 5
            save_callback(tree)
            progress.advance(task)
            progress.update(
                task,
                description=f"展开知识点... [{section.id}] {section.title[:30]}",
            )

    total_leaves = tree.count_leaves()
    console.print(f"  [green]✓ 共生成 {total_leaves} 个知识点[/green]")
    return tree


# ── 内部辅助函数 ──────────────────────────────────────────────────────────────

def _make_llm(cfg: AppConfig) -> LLMClient:
    """根据 AppConfig 构造 LLMClient。"""
    return LLMClient(
        api_key=cfg.anthropic_api_key,
        model=cfg.llm.model,
        max_tokens=cfg.llm.max_tokens,
        temperature=cfg.llm.temperature,
    )


def _make_progress() -> Progress:
    """构造统一风格的 rich 进度条。"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=False,
    )


def _expand_node(
    llm: LLMClient,
    parent: KnowledgeNode,
    siblings: list[str],
    target_level: int,
    lang: str,
    count_hint: str,
) -> list[KnowledgeNode]:
    """
    调用 Claude，将单个父节点分解为子节点列表。

    参数:
        llm:          LLMClient 实例
        parent:       待分解的父节点
        siblings:     同级其他节点的标题列表（用于去重 prompt）
        target_level: 子节点的目标 level（2 或 3）
        lang:         输出语言
        count_hint:   期望的子节点数量范围

    返回:
        list[KnowledgeNode]，level=target_level，children=[]
    """
    # 根据目标 level 选择 prompt
    if target_level == 2:
        user_prompt = build_expand_level2_prompt(
            parent_title=parent.title,
            parent_summary=parent.summary,
            parent_id=parent.id,
            siblings=siblings,
            lang=lang,
            count_hint=count_hint,
        )
    else:
        user_prompt = build_expand_level3_prompt(
            parent_title=parent.title,
            parent_summary=parent.summary,
            parent_id=parent.id,
            siblings=siblings,
            lang=lang,
            count_hint=count_hint,
        )

    messages = [{"role": "user", "content": user_prompt}]

    # 不使用搜索工具，只用 submit_nodes 终止工具
    _, tool_input = llm.run_tool_loop(
        messages=messages,
        tools=TREE_BUILDER_TOOLS,
        tool_dispatcher=_noop_dispatcher,
        system=TREE_BUILDER_SYSTEM,
        terminal_tool="submit_nodes",
    )

    if not tool_input or "nodes" not in tool_input:
        raise RuntimeError(
            f"tree_builder: 节点 [{parent.id}] {parent.title} "
            f"未收到 submit_nodes 调用或格式错误"
        )

    return _parse_nodes(tool_input["nodes"], target_level)


def _noop_dispatcher(tool_name: str, tool_input: dict[str, Any]) -> str:
    """
    空 dispatcher：tree_builder 阶段不使用搜索工具。

    如果 Claude 意外调用了未知工具，返回说明而不崩溃。
    """
    return f"（工具 '{tool_name}' 在此阶段不可用）"


def _parse_nodes(
    nodes_data: list,
    level: int,
) -> list[KnowledgeNode]:
    """
    将 submit_nodes 返回的 nodes 列表解析为 KnowledgeNode 对象。

    参数:
        nodes_data: Claude 通过 submit_nodes 提交的节点列表（应为 list[dict]）
        level:      目标 level（2 或 3）

    返回:
        list[KnowledgeNode]，children=[]
    """
    nodes = []
    for i, item in enumerate(nodes_data, 1):
        # 防御性处理：Claude 偶尔会返回字符串而非对象（schema 验证不完全）
        if not isinstance(item, dict):
            console.print(f"  [yellow]警告: submit_nodes 第 {i} 项不是对象（类型: {type(item).__name__}），跳过[/yellow]")
            continue
        node = KnowledgeNode(
            id=str(item.get("id", f"x.{i}")),
            title=item.get("title", f"节点 {i}"),
            level=level,
            summary=item.get("summary", ""),
            importance=max(1, min(5, int(item.get("importance", 3)))),
            children=[],
        )
        nodes.append(node)
    return nodes
