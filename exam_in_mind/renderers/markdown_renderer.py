"""
单文件 Markdown 渲染器

将 ExamTree 渲染为一个完整的 Markdown 文件（full.md），
包含目录、章节标题、LaTeX 公式、易错点等。
可导入 Obsidian / Notion / VS Code 直接阅读。

主要函数：render_full_markdown()
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from exam_in_mind.models import ExamTree, KnowledgeNode

console = Console()


def render_full_markdown(tree: ExamTree, output_path: Path) -> None:
    """
    将 ExamTree 渲染为单文件 Markdown。

    参数:
        tree:        完整的 ExamTree 对象（所有叶子应已填充 content）
        output_path: 输出文件路径（如 output/ap_calculus_bc/full.md）
    """
    console.print(f"\n[bold cyan]Step 7: 生成单文件 Markdown[/bold cyan]")

    lines: list[str] = []

    # 文档标题
    lines.append(f"# {tree.exam_name}")
    lines.append("")
    lines.append(f"> 语言: {tree.language} | 生成时间: {tree.generated_at}")
    lines.append("")

    # 目录
    lines.append("## 目录")
    lines.append("")
    for unit in tree.root_nodes:
        lines.append(f"- **{unit.id}. {unit.title}**")
        for section in unit.children:
            lines.append(f"  - {section.id} {section.title}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 逐 Unit 渲染
    for unit in tree.root_nodes:
        _render_unit(unit, lines)

    # 写入文件
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines)
    output_path.write_text(content, encoding="utf-8")

    console.print(f"  [green]✓ 已生成: {output_path}[/green]")
    console.print(f"  [dim]文件大小: {len(content):,} 字符[/dim]")


def _render_unit(unit: KnowledgeNode, lines: list[str]) -> None:
    """渲染一个 level=1 Unit 及其所有子节点。"""
    lines.append(f"## {unit.id}. {unit.title}")
    lines.append("")
    lines.append(f"*{unit.summary}*")
    lines.append(f"（重要度: {'⭐' * unit.importance}）")
    lines.append("")

    for section in unit.children:
        _render_section(section, lines)

    lines.append("---")
    lines.append("")


def _render_section(section: KnowledgeNode, lines: list[str]) -> None:
    """渲染一个 level=2 Section 及其所有子节点。"""
    lines.append(f"### {section.id} {section.title}")
    lines.append("")
    lines.append(f"*{section.summary}*")
    lines.append("")

    for leaf in section.children:
        _render_leaf(leaf, lines)


def _render_leaf(leaf: KnowledgeNode, lines: list[str]) -> None:
    """渲染一个 level=3 叶子知识点及其 LeafContent。"""
    lines.append(f"#### {leaf.id} {leaf.title}")
    lines.append("")

    if not leaf.content:
        lines.append("*（内容未生成）*")
        lines.append("")
        return

    c = leaf.content

    # 定义
    lines.append("**定义**")
    lines.append("")
    lines.append(c.definition)
    lines.append("")

    # 公式
    if c.formulas:
        lines.append("**核心公式**")
        lines.append("")
        for formula in c.formulas:
            # 如果公式本身没有用 $ 包裹，加上 $$ 块级显示
            stripped = formula.strip()
            if stripped.startswith("$$") or stripped.startswith("$"):
                lines.append(f"- {stripped}")
            else:
                lines.append(f"- ${stripped}$")
        lines.append("")

    # 易错点
    if c.common_mistakes:
        lines.append("**易错点**")
        lines.append("")
        for mistake in c.common_mistakes:
            lines.append(f"- ⚠️ {mistake}")
        lines.append("")

    # 来源
    if c.sources:
        lines.append("**参考来源**")
        lines.append("")
        for source in c.sources:
            lines.append(f"- {source}")
        lines.append("")
