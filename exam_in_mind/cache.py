"""
JSON 缓存读写模块

负责将 ExamTree 序列化为 tree.json，以及从磁盘加载恢复。
支持断点续跑：通过检查树结构推断已完成到第几步（对应 SPEC 第 5 节的 8 步流程）。
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

from exam_in_mind.models import ExamTree

console = Console()


def save_tree(tree: ExamTree, path: Path) -> None:
    """
    将 ExamTree 序列化并写入 JSON 文件。

    输出格式为人类可读（indent=2，ensure_ascii=False）。
    写入前先写临时文件再原子替换，避免写入中途崩溃导致文件损坏。

    参数:
        tree: 要保存的 ExamTree 对象
        path: 目标文件路径（如 output/ap_calculus_bc/tree.json）
    """
    # 确保父目录存在
    path.parent.mkdir(parents=True, exist_ok=True)

    # 先写临时文件，再原子替换，防止写到一半崩溃
    tmp_path = path.with_suffix(".tmp")
    try:
        data = tree.model_dump()
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp_path.replace(path)
    except Exception as e:
        # 清理临时文件
        if tmp_path.exists():
            tmp_path.unlink()
        raise RuntimeError(f"保存 tree.json 失败: {e}") from e


def load_tree(path: Path) -> Optional[ExamTree]:
    """
    从 JSON 文件加载 ExamTree。

    参数:
        path: tree.json 文件路径

    返回:
        成功时返回 ExamTree 对象；
        文件不存在返回 None；
        JSON 损坏或结构不符时打印错误并返回 None（不崩溃）。
    """
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tree = ExamTree.model_validate(data)
        return tree

    except json.JSONDecodeError as e:
        console.print(f"[red]错误: tree.json 格式损坏，无法解析 JSON: {e}[/red]")
        console.print("[yellow]提示: 可删除该文件后重新运行，或使用 --restart 参数。[/yellow]")
        return None

    except Exception as e:
        console.print(f"[red]错误: 加载 tree.json 失败: {e}[/red]")
        console.print("[yellow]提示: 可删除该文件后重新运行，或使用 --restart 参数。[/yellow]")
        return None


def get_progress(tree: ExamTree) -> int:
    """
    通过检查树结构，推断已完成到 SPEC 第 5 节第几步。

    对应关系（仅能判断结构相关的步骤，Step 7/8 需检查文件系统）：
        0 → 空树，尚未开始
        3 → 已有 level=1 节点（outline_builder 完成）
        4 → 已有 level=2 节点（expand_to_level_2 完成）
        5 → 已有 level=3 节点（expand_to_level_3 完成）
        6 → 所有叶子节点的 content 已填充（content_builder 完成）

    参数:
        tree: 当前的 ExamTree 对象

    返回:
        int，已完成的最后一步编号（0、3、4、5、6 之一）
    """
    if not tree.root_nodes:
        return 0

    # 检查是否有 level=2 节点
    has_level_2 = any(
        len(node.children) > 0 for node in tree.root_nodes
    )
    if not has_level_2:
        return 3

    # 检查是否有 level=3 节点
    has_level_3 = any(
        len(child.children) > 0 or child.level == 3
        for node in tree.root_nodes
        for child in node.children
    )
    if not has_level_3:
        return 4

    # 检查所有叶子节点是否都已填充 content
    leaves = tree.all_leaves()
    if not leaves:
        return 5  # 有 level=3 节点但结构异常，保守报告为 step 5

    all_filled = all(leaf.has_content() for leaf in leaves)
    if all_filled:
        return 6

    # 部分填充也报告为 step 5（content_builder 尚未完成）
    return 5


def get_progress_description(step: int) -> str:
    """
    返回步骤编号对应的人类可读描述。

    参数:
        step: get_progress() 返回的步骤编号

    返回:
        描述字符串
    """
    descriptions = {
        0: "尚未开始",
        3: "已完成：一级 Unit 框架（Step 3）",
        4: "已完成：二级节（Step 4）",
        5: "已完成：三级知识点（Step 5）",
        6: "已完成：叶子内容生成（Step 6）",
    }
    return descriptions.get(step, f"未知进度（Step {step}）")


def backup_tree(path: Path) -> Path:
    """
    将现有 tree.json 备份为带时间戳的文件名。

    参数:
        path: 原始 tree.json 路径

    返回:
        备份文件的路径
    """
    if not path.exists():
        raise FileNotFoundError(f"备份失败：{path} 不存在")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"tree_backup_{timestamp}.json")
    shutil.copy2(path, backup_path)
    console.print(f"[dim]已备份原缓存至: {backup_path}[/dim]")
    return backup_path
