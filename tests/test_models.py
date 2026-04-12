"""
数据模型测试

测试 KnowledgeNode、LeafContent、ExamTree 的创建、验证和辅助方法。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from exam_in_mind.models import ExamTree, KnowledgeNode, LeafContent


# ── 测试数据工厂 ──────────────────────────────────────────────────────────────

def make_leaf_content() -> LeafContent:
    return LeafContent(
        definition="极限 $\\lim_{x \\to a} f(x) = L$ 的定义",
        formulas=["$\\lim_{x \\to a} f(x) = L$"],
        common_mistakes=["混淆极限值与函数值", "忘记检验左右极限"],
        sources=["https://example.com"],
    )


def make_leaf_node(node_id: str = "1.1.1", with_content: bool = False) -> KnowledgeNode:
    return KnowledgeNode(
        id=node_id,
        title="极限的定义",
        level=3,
        summary="理解极限的 epsilon-delta 定义",
        importance=5,
        content=make_leaf_content() if with_content else None,
    )


def make_section_node(node_id: str = "1.1") -> KnowledgeNode:
    return KnowledgeNode(
        id=node_id,
        title="极限与连续性",
        level=2,
        summary="极限的基本概念与连续函数",
        children=[make_leaf_node("1.1.1"), make_leaf_node("1.1.2")],
    )


def make_unit_node(node_id: str = "1") -> KnowledgeNode:
    return KnowledgeNode(
        id=node_id,
        title="Unit 1: Limits and Continuity",
        level=1,
        summary="微积分的基础：极限与连续",
        children=[make_section_node("1.1"), make_section_node("1.2")],
    )


def make_exam_tree() -> ExamTree:
    return ExamTree(
        exam_name="AP Calculus BC",
        language="zh",
        generated_at="2026-04-11T00:00:00",
        root_nodes=[make_unit_node("1"), make_unit_node("2")],
    )


# ── LeafContent 测试 ──────────────────────────────────────────────────────────

def test_leaf_content_creation():
    """LeafContent 应能正常创建，字段值正确。"""
    content = make_leaf_content()
    assert "极限" in content.definition
    assert len(content.formulas) == 1
    assert len(content.common_mistakes) == 2
    assert len(content.sources) == 1


def test_leaf_content_defaults():
    """LeafContent 的可选字段应有合理默认值。"""
    content = LeafContent(definition="测试定义")
    assert content.formulas == []
    assert content.common_mistakes == []
    assert content.sources == []


def test_leaf_content_requires_definition():
    """LeafContent 缺少 definition 时应抛出 ValidationError。"""
    with pytest.raises(ValidationError):
        LeafContent()  # type: ignore


# ── KnowledgeNode 测试 ────────────────────────────────────────────────────────

def test_knowledge_node_creation():
    """KnowledgeNode 应能正常创建，字段值正确。"""
    node = make_leaf_node()
    assert node.id == "1.1.1"
    assert node.level == 3
    assert node.importance == 5


def test_knowledge_node_default_importance():
    """KnowledgeNode 的 importance 默认值应为 3。"""
    node = KnowledgeNode(id="1", title="测试", level=1, summary="摘要")
    assert node.importance == 3


def test_knowledge_node_level_validation():
    """level 必须在 1-3 之间，否则抛出 ValidationError。"""
    with pytest.raises(ValidationError):
        KnowledgeNode(id="1", title="测试", level=0, summary="摘要")
    with pytest.raises(ValidationError):
        KnowledgeNode(id="1", title="测试", level=4, summary="摘要")


def test_knowledge_node_importance_validation():
    """importance 必须在 1-5 之间，否则抛出 ValidationError。"""
    with pytest.raises(ValidationError):
        KnowledgeNode(id="1", title="测试", level=1, summary="摘要", importance=0)
    with pytest.raises(ValidationError):
        KnowledgeNode(id="1", title="测试", level=1, summary="摘要", importance=6)


def test_knowledge_node_is_leaf():
    """is_leaf() 应正确识别叶子节点。"""
    leaf = make_leaf_node()
    assert leaf.is_leaf() is True

    section = make_section_node()
    assert section.is_leaf() is False


def test_knowledge_node_has_content():
    """has_content() 应正确识别是否已填充内容。"""
    leaf_no_content = make_leaf_node(with_content=False)
    assert leaf_no_content.has_content() is False

    leaf_with_content = make_leaf_node(with_content=True)
    assert leaf_with_content.has_content() is True


def test_knowledge_node_iter_leaves():
    """iter_leaves() 应递归收集所有叶子节点。"""
    unit = make_unit_node()
    # unit → 2 sections → 各 2 leaves = 4 leaves
    leaves = unit.iter_leaves()
    assert len(leaves) == 4
    assert all(leaf.level == 3 for leaf in leaves)


def test_knowledge_node_recursive_children():
    """KnowledgeNode 应支持多层嵌套（递归结构）。"""
    unit = make_unit_node()
    assert len(unit.children) == 2
    assert len(unit.children[0].children) == 2
    assert unit.children[0].children[0].level == 3


# ── ExamTree 测试 ─────────────────────────────────────────────────────────────

def test_exam_tree_creation():
    """ExamTree 应能正常创建，基本字段正确。"""
    tree = make_exam_tree()
    assert tree.exam_name == "AP Calculus BC"
    assert tree.language == "zh"
    assert len(tree.root_nodes) == 2


def test_exam_tree_all_leaves():
    """all_leaves() 应收集整棵树的所有叶子节点。"""
    tree = make_exam_tree()
    # 2 units × 2 sections × 2 leaves = 8
    leaves = tree.all_leaves()
    assert len(leaves) == 8
    assert all(leaf.level == 3 for leaf in leaves)


def test_exam_tree_count_leaves():
    """count_leaves() 应返回正确的叶子数量。"""
    tree = make_exam_tree()
    assert tree.count_leaves() == 8


def test_exam_tree_count_filled_leaves():
    """count_filled_leaves() 应只统计已填充 content 的叶子。"""
    tree = make_exam_tree()
    assert tree.count_filled_leaves() == 0

    # 给第一个叶子填充内容
    tree.root_nodes[0].children[0].children[0].content = make_leaf_content()
    assert tree.count_filled_leaves() == 1


def test_exam_tree_empty_root_nodes():
    """ExamTree 允许 root_nodes 为空列表（初始状态）。"""
    tree = ExamTree(
        exam_name="Test Exam",
        language="zh",
        generated_at="2026-01-01T00:00:00",
    )
    assert tree.root_nodes == []
    assert tree.count_leaves() == 0
