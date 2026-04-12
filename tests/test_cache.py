"""
缓存系统测试

测试 save_tree / load_tree / get_progress / backup_tree 的行为。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exam_in_mind.cache import (
    backup_tree,
    get_progress,
    get_progress_description,
    load_tree,
    save_tree,
)
from exam_in_mind.models import ExamTree, KnowledgeNode, LeafContent


# ── 测试数据工厂 ──────────────────────────────────────────────────────────────

def make_minimal_tree() -> ExamTree:
    """构造一棵空树（仅有基本信息，无节点）。"""
    return ExamTree(
        exam_name="AP Calculus BC",
        language="zh",
        generated_at="2026-04-11T00:00:00",
    )


def make_level1_tree() -> ExamTree:
    """构造只有 level=1 节点的树（outline 阶段完成）。"""
    tree = make_minimal_tree()
    tree.root_nodes = [
        KnowledgeNode(id="1", title="Unit 1", level=1, summary="极限"),
        KnowledgeNode(id="2", title="Unit 2", level=1, summary="导数"),
    ]
    return tree


def make_level2_tree() -> ExamTree:
    """构造有 level=1 和 level=2 节点的树。"""
    tree = make_level1_tree()
    tree.root_nodes[0].children = [
        KnowledgeNode(id="1.1", title="Section 1.1", level=2, summary="极限定义"),
    ]
    return tree


def make_level3_tree() -> ExamTree:
    """构造有三层节点的树（level=1/2/3），叶子无 content。"""
    tree = make_level2_tree()
    tree.root_nodes[0].children[0].children = [
        KnowledgeNode(id="1.1.1", title="极限定义", level=3, summary="epsilon-delta"),
        KnowledgeNode(id="1.1.2", title="极限计算", level=3, summary="代入法"),
    ]
    return tree


def make_full_tree() -> ExamTree:
    """构造所有叶子都有 content 的完整树。"""
    tree = make_level3_tree()
    content = LeafContent(
        definition="极限的定义",
        formulas=["$\\lim_{x \\to a} f(x) = L$"],
        common_mistakes=["混淆极限与函数值"],
    )
    for leaf in tree.all_leaves():
        leaf.content = content.model_copy()
    return tree


# ── save_tree / load_tree 测试 ────────────────────────────────────────────────

def test_save_and_load_roundtrip(tmp_path: Path):
    """保存后加载，数据应完全一致。"""
    tree = make_level3_tree()
    path = tmp_path / "tree.json"

    save_tree(tree, path)
    loaded = load_tree(path)

    assert loaded is not None
    assert loaded.exam_name == tree.exam_name
    assert loaded.language == tree.language
    assert len(loaded.root_nodes) == len(tree.root_nodes)
    assert len(loaded.root_nodes[0].children) == 1
    assert len(loaded.root_nodes[0].children[0].children) == 2


def test_save_creates_parent_directory(tmp_path: Path):
    """save_tree 应自动创建不存在的父目录。"""
    tree = make_minimal_tree()
    path = tmp_path / "nested" / "deep" / "tree.json"

    save_tree(tree, path)
    assert path.exists()


def test_save_is_human_readable(tmp_path: Path):
    """生成的 tree.json 应有缩进（indent=2）且中文不转义。"""
    tree = make_minimal_tree()
    tree.exam_name = "AP微积分BC"
    path = tmp_path / "tree.json"

    save_tree(tree, path)
    raw = path.read_text(encoding="utf-8")

    # 有缩进
    assert "  " in raw
    # 中文不转义（ensure_ascii=False）
    assert "AP微积分BC" in raw


def test_load_returns_none_for_missing_file(tmp_path: Path):
    """文件不存在时 load_tree 应返回 None，不崩溃。"""
    result = load_tree(tmp_path / "nonexistent.json")
    assert result is None


def test_load_returns_none_for_corrupted_json(tmp_path: Path):
    """JSON 格式损坏时 load_tree 应返回 None，不崩溃。"""
    path = tmp_path / "tree.json"
    path.write_text("{ invalid json !!!", encoding="utf-8")

    result = load_tree(path)
    assert result is None


def test_load_returns_none_for_wrong_schema(tmp_path: Path):
    """JSON 合法但结构不符合 ExamTree 时 load_tree 应返回 None，不崩溃。"""
    path = tmp_path / "tree.json"
    # 缺少必填字段 exam_name
    path.write_text(json.dumps({"language": "zh"}), encoding="utf-8")

    result = load_tree(path)
    assert result is None


def test_save_with_leaf_content(tmp_path: Path):
    """含 LeafContent 的树保存后加载，content 字段应正确恢复。"""
    tree = make_full_tree()
    path = tmp_path / "tree.json"

    save_tree(tree, path)
    loaded = load_tree(path)

    assert loaded is not None
    leaves = loaded.all_leaves()
    assert len(leaves) == 2
    assert all(leaf.has_content() for leaf in leaves)
    assert leaves[0].content.definition == "极限的定义"
    assert "$\\lim_{x \\to a} f(x) = L$" in leaves[0].content.formulas


# ── get_progress 测试 ─────────────────────────────────────────────────────────

def test_get_progress_empty_tree():
    """空树应返回进度 0。"""
    assert get_progress(make_minimal_tree()) == 0


def test_get_progress_level1():
    """只有 level=1 节点应返回进度 3。"""
    assert get_progress(make_level1_tree()) == 3


def test_get_progress_level2():
    """有 level=2 节点应返回进度 4。"""
    assert get_progress(make_level2_tree()) == 4


def test_get_progress_level3_no_content():
    """有 level=3 节点但无 content 应返回进度 5。"""
    assert get_progress(make_level3_tree()) == 5


def test_get_progress_all_content_filled():
    """所有叶子节点都有 content 应返回进度 6。"""
    assert get_progress(make_full_tree()) == 6


def test_get_progress_description():
    """get_progress_description 应返回非空字符串。"""
    for step in [0, 3, 4, 5, 6]:
        desc = get_progress_description(step)
        assert isinstance(desc, str)
        assert len(desc) > 0


# ── backup_tree 测试 ──────────────────────────────────────────────────────────

def test_backup_tree_creates_backup(tmp_path: Path):
    """backup_tree 应创建带时间戳的备份文件。"""
    tree = make_minimal_tree()
    path = tmp_path / "tree.json"
    save_tree(tree, path)

    backup_path = backup_tree(path)

    assert backup_path.exists()
    assert "backup" in backup_path.name
    # 原文件仍然存在
    assert path.exists()


def test_backup_tree_raises_if_not_exists(tmp_path: Path):
    """原文件不存在时 backup_tree 应抛出 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        backup_tree(tmp_path / "nonexistent.json")
