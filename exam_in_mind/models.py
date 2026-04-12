"""
数据模型模块

定义知识树的核心 Pydantic 数据结构，严格按照 SPEC 第 4 节。
所有模型均支持 JSON 序列化/反序列化，用于 tree.json 缓存文件的读写。
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class LeafContent(BaseModel):
    """
    叶子知识点的详细内容。

    仅在 level=3 的 KnowledgeNode 上填充。
    包含定义、公式（LaTeX）、易错点、来源 URL。
    """

    definition: str = Field(..., description="知识点定义，支持 LaTeX")
    formulas: list[str] = Field(
        default_factory=list,
        description="核心公式/定理列表，LaTeX 格式",
    )
    common_mistakes: list[str] = Field(
        default_factory=list,
        description="易错点列表",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="引用来源 URL（可选）",
    )


class KnowledgeNode(BaseModel):
    """
    知识树节点，可递归嵌套。

    level=1: 章（Unit）
    level=2: 节（Section）
    level=3: 知识点（Leaf），此时 content 字段应被填充
    """

    id: str = Field(..., description="层级编号，如 '1'、'1.2'、'1.2.3'")
    title: str = Field(..., description="节点标题")
    level: int = Field(..., ge=1, le=3, description="1=章, 2=节, 3=知识点")
    summary: str = Field(..., description="一句话简介")
    importance: int = Field(
        default=3,
        ge=1,
        le=5,
        description="考试重要度 1-5，5 为最高",
    )
    children: list["KnowledgeNode"] = Field(default_factory=list)
    content: Optional[LeafContent] = Field(
        default=None,
        description="仅叶子节点（level=3）填充",
    )

    def is_leaf(self) -> bool:
        """判断节点是否为叶子节点（level=3 且无子节点）。"""
        return self.level == 3 and len(self.children) == 0

    def has_content(self) -> bool:
        """判断叶子节点的内容是否已生成。"""
        return self.content is not None

    def iter_leaves(self) -> list["KnowledgeNode"]:
        """
        递归收集当前节点下的所有叶子节点。

        返回:
            list[KnowledgeNode]，所有 level=3 的节点
        """
        if self.is_leaf():
            return [self]
        leaves = []
        for child in self.children:
            leaves.extend(child.iter_leaves())
        return leaves


# 让 KnowledgeNode 支持自引用（递归模型）
KnowledgeNode.model_rebuild()


class ExamTree(BaseModel):
    """
    完整知识树根对象，也是 tree.json 的顶层结构。

    包含考试基本信息、所有根节点（level=1），以及元数据（考纲版本、模型名等）。
    """

    exam_name: str = Field(..., description="考试名称，如 'AP Calculus BC'")
    language: str = Field(..., description="内容语言，如 'zh'")
    generated_at: str = Field(..., description="创建时间，ISO 8601 格式")
    root_nodes: list[KnowledgeNode] = Field(default_factory=list)
    metadata: dict = Field(
        default_factory=dict,
        description="考纲版本、模型名、进度标记等元数据",
    )

    def all_leaves(self) -> list[KnowledgeNode]:
        """
        收集整棵树的所有叶子节点（level=3）。

        返回:
            list[KnowledgeNode]
        """
        leaves = []
        for node in self.root_nodes:
            leaves.extend(node.iter_leaves())
        return leaves

    def count_leaves(self) -> int:
        """返回叶子节点总数。"""
        return len(self.all_leaves())

    def count_filled_leaves(self) -> int:
        """返回已生成 content 的叶子节点数量。"""
        return sum(1 for leaf in self.all_leaves() if leaf.has_content())
