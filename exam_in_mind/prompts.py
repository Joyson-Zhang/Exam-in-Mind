"""
Prompt 模板模块

集中管理所有发送给 Claude 的 system prompt 和 user prompt 模板。
使用 Python 函数而非纯字符串，方便传入动态参数。

规则：
- 所有 prompt 函数名以 `build_` 开头
- system prompt 和 user prompt 分开定义
- 不在业务代码中硬编码 prompt 内容
"""

from __future__ import annotations


# ── Phase 4: outline_builder prompt ──────────────────────────────────────────

OUTLINE_BUILDER_SYSTEM = """你是一个专业的考试备考助手，擅长整理考试大纲和知识体系。
你的任务是通过搜索获取指定考试的最新官方考纲，然后整理出顶层的知识框架。

工作规则：
1. 使用 search_web 工具查询官方考纲信息（建议搜索英文关键词获得更准确的结果）
2. 搜索 1-3 次后，调用 submit_outline 工具提交最终结构化结果
3. 每个 Unit 的 importance 按照在考试中的占比和重要程度评分（1-5分）
4. summary 用目标语言写一句简短的介绍
5. 严格遵循考试官方考纲的 Unit 划分，不要自行合并或拆分"""


def build_outline_user_prompt(exam_name: str, lang: str, count_hint: str) -> str:
    """
    构造 outline_builder 的用户 prompt。

    参数:
        exam_name:  考试名称，如 'AP Calculus BC'
        lang:       输出语言，如 'zh'（中文）
        count_hint: 期望的 Unit 数量范围，如 '8-12'

    返回:
        格式化的用户 prompt 字符串
    """
    lang_desc = "中文" if lang == "zh" else "English"
    return f"""请帮我整理 {exam_name} 的考试大纲框架。

要求：
- 搜索 {exam_name} 的最新官方考纲（Course and Exam Description / CED）
- 整理出顶层的 Unit 列表，预计 {count_hint} 个 Unit
- title 使用考纲官方名称（英文）
- summary 用{lang_desc}写一句话介绍该 Unit 的核心内容
- importance 根据该 Unit 在考试中的权重打分（1-5）
- 完成后调用 submit_outline 工具提交结果

请开始搜索并整理 {exam_name} 的 Unit 框架。"""


# ── Phase 5: tree_builder prompt ─────────────────────────────────────────────

TREE_BUILDER_SYSTEM = """你是一个专业的考试备考助手，擅长分解和细化考试知识点。
你的任务是将考试大纲的 Unit 进一步分解为章节（Section）或知识点。

工作规则：
1. 严格基于给定的父节点信息进行分解，不要引入考纲范围之外的内容
2. 分解要有逻辑层次，同级节点之间不重叠
3. 调用 submit_nodes 工具提交结构化结果
4. summary 要简明扼要，一句话说清该节点的核心内容
5. importance 继承并细化父节点的重要性评分"""


def build_expand_level2_prompt(
    parent_title: str,
    parent_summary: str,
    parent_id: str,
    siblings: list[str],
    lang: str,
    count_hint: str,
) -> str:
    """
    构造将 level=1 节点展开为 level=2 子节点的 prompt。

    参数:
        parent_title:   父节点标题
        parent_summary: 父节点摘要
        parent_id:      父节点 id（如 '3'）
        siblings:       同级其他 Unit 的标题列表（用于去重提示）
        lang:           输出语言
        count_hint:     期望的子节点数量范围

    返回:
        格式化的用户 prompt 字符串
    """
    lang_desc = "中文" if lang == "zh" else "English"
    siblings_str = "\n".join(f"- {s}" for s in siblings) if siblings else "（无其他 Unit）"

    return f"""请将以下考试 Unit 分解为 Section（节）。

**当前 Unit：**
- ID: {parent_id}
- 标题: {parent_title}
- 简介: {parent_summary}

**同级其他 Unit（请确保内容不重叠）：**
{siblings_str}

**要求：**
- 分解为 {count_hint} 个 Section
- 每个 Section 的 id 格式为 "{parent_id}.1", "{parent_id}.2" ...
- title 使用英文或专业术语（参考 AP 考纲命名风格）
- summary 用{lang_desc}写一句话
- importance 在 1-5 之间评分
- 调用 submit_nodes 工具提交结果"""


def build_expand_level3_prompt(
    parent_title: str,
    parent_summary: str,
    parent_id: str,
    siblings: list[str],
    lang: str,
    count_hint: str,
) -> str:
    """
    构造将 level=2 节点展开为 level=3 知识点的 prompt。

    参数:
        parent_title:   父节点（Section）标题
        parent_summary: 父节点摘要
        parent_id:      父节点 id（如 '3.2'）
        siblings:       同级其他 Section 的标题列表
        lang:           输出语言
        count_hint:     期望的子节点数量范围

    返回:
        格式化的用户 prompt 字符串
    """
    lang_desc = "中文" if lang == "zh" else "English"
    siblings_str = "\n".join(f"- {s}" for s in siblings) if siblings else "（无其他 Section）"

    return f"""请将以下考试 Section 分解为具体知识点（Knowledge Points）。

**当前 Section：**
- ID: {parent_id}
- 标题: {parent_title}
- 简介: {parent_summary}

**同级其他 Section（请确保内容不重叠）：**
{siblings_str}

**要求：**
- 分解为 {count_hint} 个知识点
- 每个知识点的 id 格式为 "{parent_id}.1", "{parent_id}.2" ...
- title 使用简洁的专业术语（中英文均可）
- summary 用{lang_desc}写一句话说明该知识点的核心
- importance 在 1-5 之间评分
- 调用 submit_nodes 工具提交结果"""


# ── Phase 6: content_builder prompt ──────────────────────────────────────────

CONTENT_BUILDER_SYSTEM = """你是一个专业的考试备考内容生成助手，擅长用清晰、准确的语言讲解数学和科学概念。
你的任务是为给定的考试知识点生成详细的学习内容。

工作规则：
1. definition 要准确、完整，包含必要的数学符号（使用 LaTeX）
2. formulas 列出该知识点的核心公式和定理，每条都是完整的 LaTeX 表达式
3. common_mistakes 列出学生在考试中最容易犯的 2-4 个错误
4. 调用 submit_content 工具提交结构化结果
5. 所有内容用目标语言写，公式用标准 LaTeX"""


def build_leaf_content_prompt(
    node_title: str,
    node_summary: str,
    node_id: str,
    parent_path: str,
    lang: str,
) -> str:
    """
    构造为叶子知识点生成 LeafContent 的 prompt。

    参数:
        node_title:   知识点标题
        node_summary: 知识点摘要
        node_id:      知识点 id
        parent_path:  父节点路径（如 'Unit 1 > Section 1.2'）
        lang:         输出语言

    返回:
        格式化的用户 prompt 字符串
    """
    lang_desc = "中文" if lang == "zh" else "English"
    return f"""请为以下考试知识点生成详细的学习内容。

**知识点信息：**
- ID: {node_id}
- 标题: {node_title}
- 所属路径: {parent_path}
- 简介: {node_summary}

**要求：**
- definition：用{lang_desc}写出完整、准确的定义，可包含 LaTeX 公式（用 $...$ 包裹）
- formulas：列出 1-5 条核心公式或定理，每条都是完整的 LaTeX 字符串（如 "$f'(x) = \\lim_{{h \\to 0}} \\frac{{f(x+h)-f(x)}}{{h}}$"）
- common_mistakes：列出 2-4 条学生在 AP 考试中常见的错误或易混淆点
- 调用 submit_content 工具提交结果"""
