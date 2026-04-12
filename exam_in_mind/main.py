"""
命令行入口模块

定义 exam-in-mind 的所有命令行参数，加载配置，并串联各构建步骤。
当前实现到 Phase 4（outline_builder），后续 Phase 将逐步追加。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import click
from rich.console import Console

from exam_in_mind.config import AppConfig

console = Console()


def _exam_slug(exam_name: str) -> str:
    """
    将考试名称转换为适合作为目录名的 slug。

    示例: 'AP Calculus BC' → 'ap_calculus_bc'

    参数:
        exam_name: 原始考试名称

    返回:
        小写、下划线分隔的 slug 字符串
    """
    slug = exam_name.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug


@click.command()
@click.option(
    "--exam",
    required=True,
    help="考试名称，例如: 'AP Calculus BC'",
)
@click.option(
    "--lang",
    default="zh",
    show_default=True,
    help="输出语言，默认中文 (zh)",
)
@click.option(
    "--model",
    default=None,
    help="覆盖 config.yaml 中的模型名称",
)
@click.option(
    "--no-search",
    "no_search",
    is_flag=True,
    default=False,
    help="禁用 Brave Search，仅使用模型内置知识",
)
@click.option(
    "--restart",
    is_flag=True,
    default=False,
    help="忽略已有缓存，从头开始生成",
)
@click.option(
    "--output-dir",
    "output_dir",
    default=None,
    help="自定义输出目录，覆盖 config.yaml 中的设置",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="打印详细日志和配置信息",
)
def cli(
    exam: str,
    lang: str,
    model: str | None,
    no_search: bool,
    restart: bool,
    output_dir: str | None,
    verbose: bool,
) -> None:
    """
    Exam-in-Mind: 自动构建考试知识树并生成复习站点。

    示例:
        python -m exam_in_mind --exam "AP Calculus BC"
        python -m exam_in_mind --exam "AP Calculus BC" --lang zh --no-search
    """
    console.print(f"\n[bold green]Exam-in-Mind[/bold green] 启动")
    console.print(f"考试科目: [bold]{exam}[/bold]")

    # ── Step 1: 加载配置 ──────────────────────────────────────────────────────
    cfg = AppConfig(verbose=verbose)

    # 命令行参数覆盖配置文件
    if model:
        cfg.llm.model = model
        console.print(f"[dim]模型已覆盖为: {model}[/dim]")

    if no_search:
        cfg.search.enabled = False
        console.print("[dim]搜索功能已禁用[/dim]")

    if output_dir:
        cfg.output.base_dir = output_dir

    if lang != "zh":
        cfg.output.language = lang

    # 统一使用命令行传入的 lang（命令行优先于 config）
    effective_lang = lang

    # 校验 API key
    require_brave = cfg.search.enabled
    if not cfg.validate_api_keys(require_brave=require_brave):
        console.print("[red]配置校验失败，请检查 .env 文件后重试。[/red]")
        sys.exit(1)

    if verbose:
        console.print("\n[bold cyan]=== 命令行参数 ===[/bold cyan]")
        console.print(f"  --exam       : {exam}")
        console.print(f"  --lang       : {lang}")
        console.print(f"  --model      : {model or '(使用配置文件)'}")
        console.print(f"  --no-search  : {no_search}")
        console.print(f"  --restart    : {restart}")
        console.print(f"  --output-dir : {output_dir or '(使用配置文件)'}")
        console.print(f"  --verbose    : {verbose}")
        console.print()

    # ── Step 2: 确定输出路径，检查缓存 ───────────────────────────────────────
    slug = _exam_slug(exam)
    base_dir = Path(cfg.output.base_dir)
    exam_dir = base_dir / slug
    tree_path = exam_dir / "tree.json"

    exam_dir.mkdir(parents=True, exist_ok=True)

    # 导入缓存模块
    from exam_in_mind.cache import (
        backup_tree,
        get_progress,
        get_progress_description,
        load_tree,
        save_tree,
    )
    from exam_in_mind.models import ExamTree

    # 检查已有缓存
    existing_tree = None
    if tree_path.exists() and not restart:
        existing_tree = load_tree(tree_path)
        if existing_tree:
            step = get_progress(existing_tree)
            desc = get_progress_description(step)
            console.print(f"\n[yellow]检测到上次进度: {desc}（Step {step}）[/yellow]")
            answer = click.prompt(
                "是否继续上次进度？",
                type=click.Choice(["Y", "n", "restart"], case_sensitive=False),
                default="Y",
            )
            if answer.lower() == "restart":
                console.print("[dim]备份旧缓存并重新开始...[/dim]")
                backup_tree(tree_path)
                existing_tree = None
            elif answer.lower() == "n":
                console.print("[dim]已取消。[/dim]")
                sys.exit(0)
            # Y：继续使用 existing_tree

    if restart and tree_path.exists():
        backup_tree(tree_path)
        existing_tree = None

    # ── Step 3: 构建 level=1 大纲框架 ────────────────────────────────────────
    from exam_in_mind.builders.outline_builder import build_outline, make_exam_tree

    # 判断是否需要执行 Step 3
    current_step = get_progress(existing_tree) if existing_tree else 0

    if current_step < 3:
        root_nodes = build_outline(
            exam_name=exam,
            lang=effective_lang,
            cfg=cfg,
        )
        tree = make_exam_tree(
            exam_name=exam,
            lang=effective_lang,
            root_nodes=root_nodes,
            model_name=cfg.llm.model,
        )
        save_tree(tree, tree_path)
        console.print(f"  [dim]已保存快照: {tree_path}[/dim]")
    else:
        tree = existing_tree
        console.print(f"\n[dim]Step 3 已完成，跳过（当前进度: Step {current_step}）[/dim]")

    # ── Step 4: 扩展至 level=2（Section）────────────────────────────────────
    from exam_in_mind.builders.tree_builder import expand_to_level_2, expand_to_level_3

    def save_snapshot(t: ExamTree) -> None:
        """保存快照的回调函数，供 tree_builder 在每个节点完成后调用。"""
        save_tree(t, tree_path)

    # Step 4：current_step < 5 才需要运行（expand 内部会跳过已展开节点）
    # 如果 current_step == 4 说明 Step 4 只完成了一部分，仍需继续
    current_step = get_progress(tree)
    if current_step < 5:
        tree = expand_to_level_2(tree, cfg, save_snapshot)
    else:
        console.print(f"\n[dim]Step 4 已完成，跳过（当前进度: Step {current_step}）[/dim]")

    # ── Step 5: 扩展至 level=3（知识点）─────────────────────────────────────
    # Step 5：current_step < 6 才需要运行（expand 内部会跳过已展开节点）
    # 如果 current_step == 5 说明 Step 5 只完成了一部分，仍需继续
    current_step = get_progress(tree)
    if current_step < 6:
        tree = expand_to_level_3(tree, cfg, save_snapshot)
    else:
        console.print(f"\n[dim]Step 5 已完成，跳过（当前进度: Step {current_step}）[/dim]")

    # ── Step 6: 生成叶子内容 ────────────────────────────────────────────────
    from exam_in_mind.builders.content_builder import generate_all_leaves

    current_step = get_progress(tree)
    if current_step < 6:
        tree = generate_all_leaves(tree, cfg, save_snapshot)
    else:
        console.print(f"\n[dim]Step 6 已完成，跳过（当前进度: Step {current_step}）[/dim]")

    # ── Step 7: 生成单文件 Markdown ─────────────────────────────────────────
    from exam_in_mind.renderers.markdown_renderer import render_full_markdown

    full_md_path = exam_dir / "full.md"
    render_full_markdown(tree, full_md_path)

    # ── Step 8: 生成 MkDocs 站点 ──────────────────────────────────────────
    from exam_in_mind.renderers.mkdocs_renderer import render_mkdocs_site

    render_mkdocs_site(tree, exam_dir)

    # ── 完成 ─────────────────────────────────────────────────────────────────
    console.print(f"\n[bold green]===== 全部完成 =====[/bold green]")
    console.print(f"  知识树缓存   : {tree_path}")
    console.print(f"  单文件 MD    : {full_md_path}")
    console.print(f"  MkDocs 站点  : {exam_dir / 'site' / 'index.html'}")
    console.print(f"  Unit 数量    : {len(tree.root_nodes)}")
    console.print(f"  知识点总数   : {tree.count_leaves()}")
    console.print(f"  已填充内容   : {tree.count_filled_leaves()}/{tree.count_leaves()}")
    console.print()


def main() -> None:
    """python -m exam_in_mind 的入口函数。"""
    cli()


if __name__ == "__main__":
    main()
