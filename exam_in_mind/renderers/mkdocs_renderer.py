"""
MkDocs 静态站渲染器

将 ExamTree 渲染为 MkDocs 项目结构：
    - mkdocs.yml（配置文件，含 Material 主题、KaTeX、搜索）
    - docs/ 目录下的分文件 Markdown
    - 调用 mkdocs build 生成 site/

文件路径格式：docs/01-unit-name/01-section-name/01-knowledge-point.md

主要函数：render_mkdocs_site()
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from rich.console import Console

from exam_in_mind.models import ExamTree, KnowledgeNode

console = Console()


def render_mkdocs_site(tree: ExamTree, output_dir: Path) -> None:
    """
    将 ExamTree 渲染为完整的 MkDocs 站点。

    流程：
        1. 生成 mkdocs.yml
        2. 生成 docs/ 下的分文件 Markdown
        3. 调用 mkdocs build 生成 site/

    参数:
        tree:       完整的 ExamTree 对象
        output_dir: 输出目录（如 output/ap_calculus_bc/）
    """
    console.print(f"\n[bold cyan]Step 8: 生成 MkDocs 站点[/bold cyan]")

    docs_dir = output_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    # 1. 生成导航结构和文档文件
    nav = _generate_docs(tree, docs_dir)

    # 2. 生成 mkdocs.yml
    _generate_mkdocs_yml(tree, output_dir, nav)

    # 3. 生成首页
    _generate_index(tree, docs_dir)

    # 4. 调用 mkdocs build
    _run_mkdocs_build(output_dir)


def _slugify(text: str) -> str:
    """
    将标题转换为适合作为文件/目录名的 slug。

    示例: "Limits and Continuity" → "limits-and-continuity"
    """
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", slug)
    slug = slug.strip("-")
    return slug[:60]  # 限制长度


def _generate_docs(
    tree: ExamTree,
    docs_dir: Path,
) -> list:
    """
    在 docs/ 下生成分文件 Markdown，返回 mkdocs 导航结构。

    参数:
        tree:     ExamTree 对象
        docs_dir: docs/ 目录路径

    返回:
        nav 列表，用于 mkdocs.yml 的 nav 配置
    """
    nav = [{"首页": "index.md"}]

    for i, unit in enumerate(tree.root_nodes, 1):
        unit_dir_name = f"{i:02d}-{_slugify(unit.title)}"
        unit_dir = docs_dir / unit_dir_name
        unit_dir.mkdir(parents=True, exist_ok=True)

        # 生成 Unit 首页
        _write_unit_index(unit, unit_dir)

        unit_nav_items: list[dict] = [{"概述": f"{unit_dir_name}/index.md"}]

        for j, section in enumerate(unit.children, 1):
            sec_dir_name = f"{j:02d}-{_slugify(section.title)}"
            sec_dir = unit_dir / sec_dir_name
            sec_dir.mkdir(parents=True, exist_ok=True)

            # 生成 Section 首页
            _write_section_index(section, sec_dir)

            sec_nav_items: list[dict] = [{"概述": f"{unit_dir_name}/{sec_dir_name}/index.md"}]

            for k, leaf in enumerate(section.children, 1):
                leaf_file_name = f"{k:02d}-{_slugify(leaf.title)}.md"
                leaf_path = sec_dir / leaf_file_name
                _write_leaf_page(leaf, leaf_path)
                sec_nav_items.append(
                    {leaf.title: f"{unit_dir_name}/{sec_dir_name}/{leaf_file_name}"}
                )

            unit_nav_items.append({f"{section.id} {section.title}": sec_nav_items})

        nav.append({f"{unit.id}. {unit.title}": unit_nav_items})

    return nav


def _write_unit_index(unit: KnowledgeNode, unit_dir: Path) -> None:
    """生成 Unit 的 index.md 概述页面。"""
    lines = [
        f"# {unit.id}. {unit.title}",
        "",
        f"*{unit.summary}*",
        "",
        f"**重要度**: {'⭐' * unit.importance}",
        "",
        "## 本单元包含的章节",
        "",
    ]
    for section in unit.children:
        lines.append(f"- **{section.id} {section.title}** — {section.summary}")
    lines.append("")

    (unit_dir / "index.md").write_text("\n".join(lines), encoding="utf-8")


def _write_section_index(section: KnowledgeNode, sec_dir: Path) -> None:
    """生成 Section 的 index.md 概述页面。"""
    lines = [
        f"# {section.id} {section.title}",
        "",
        f"*{section.summary}*",
        "",
        "## 本节包含的知识点",
        "",
    ]
    for leaf in section.children:
        lines.append(f"- **{leaf.id} {leaf.title}** — {leaf.summary}")
    lines.append("")

    (sec_dir / "index.md").write_text("\n".join(lines), encoding="utf-8")


def _write_leaf_page(leaf: KnowledgeNode, path: Path) -> None:
    """
    生成叶子知识点的独立 Markdown 页面。

    包含定义、公式（LaTeX）、易错点、来源。
    """
    lines = [
        f"# {leaf.id} {leaf.title}",
        "",
        f"*{leaf.summary}*",
        "",
    ]

    if not leaf.content:
        lines.append("*（内容未生成）*")
        path.write_text("\n".join(lines), encoding="utf-8")
        return

    c = leaf.content

    # 定义（清理字面量转义序列）
    lines.append("## 定义")
    lines.append("")
    lines.append(_unescape_literal_newlines(c.definition))
    lines.append("")

    # 公式
    if c.formulas:
        lines.append("## 核心公式")
        lines.append("")
        for formula in c.formulas:
            normalized = _normalize_formula(formula)
            lines.append(f"- {normalized}")
        lines.append("")

    # 易错点
    if c.common_mistakes:
        lines.append("## 易错点")
        lines.append("")
        for mistake in c.common_mistakes:
            lines.append(f"- ⚠️ {mistake}")
        lines.append("")

    # 来源
    if c.sources:
        lines.append("## 参考来源")
        lines.append("")
        for source in c.sources:
            lines.append(f"- [{source}]({source})")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def _normalize_formula(formula: str) -> str:
    """
    归一化公式的 LaTeX 定界符，确保输出格式统一。

    LLM 返回的公式格式不一致，需要处理以下情况：
        1. ``$formula$``           → 已正确，原样返回
        2. ``$formula$ (说明)``    → 已正确（内含配对 $），原样返回
        3. ``$$formula$$``         → 已正确，原样返回
        4. ``$formula``            → 缺闭合 $，补上
        5. ``formula``             → 完全无定界符，包裹 $...$
    """
    stripped = formula.strip()
    if not stripped:
        return formula

    # ── Case 1: display 模式 $$...$$ ──
    if stripped.startswith("$$"):
        # 检查是否有闭合 $$
        if "$$" in stripped[2:]:
            return stripped  # 已正确
        # 缺闭合 $$，补上
        return f"{stripped}$$"

    # ── Case 2: 以 $ 开头 ──
    if stripped.startswith("$"):
        # 在首字符之后寻找配对的 $
        if "$" in stripped[1:]:
            return stripped  # 已有配对 $（可能尾部有说明文字），原样返回
        # 缺闭合 $，补上
        return f"{stripped}$"

    # ── Case 3: 完全无 $ 定界符 → 包裹 $...$ ──
    return f"${stripped}$"


def _unescape_literal_newlines(text: str) -> str:
    """
    将文本中的字面量转义序列 ``\\n`` 转换为真正的换行符。

    LLM 有时在 JSON 字符串中写入字面量 ``\\n``（两个字符: 反斜杠 + n），
    而非真正的换行符。这些字面量在 Markdown 中会显示为可见的 ``\\n`` 文本。

    使用负向前瞻 ``(?![a-zA-Z])`` 避免误伤 LaTeX 命令
    （如 ``\\neq``、``\\nu``、``\\nabla`` 等以 ``\\n`` 开头的命令）。
    """
    return re.sub(r"\\n(?![a-zA-Z])", "\n", text)


def _generate_index(tree: ExamTree, docs_dir: Path) -> None:
    """生成 docs/index.md 首页。"""
    lines = [
        f"# {tree.exam_name} 知识树",
        "",
        f"> 语言: {tree.language} | 生成时间: {tree.generated_at}",
        "",
        "## 考试大纲",
        "",
    ]

    total_leaves = tree.count_leaves()
    filled_leaves = tree.count_filled_leaves()
    lines.append(f"本知识树共包含 **{len(tree.root_nodes)}** 个 Unit、**{total_leaves}** 个知识点。")
    lines.append(f"已生成内容：{filled_leaves}/{total_leaves}。")
    lines.append("")

    for unit in tree.root_nodes:
        sec_count = len(unit.children)
        leaf_count = sum(len(s.children) for s in unit.children)
        lines.append(f"### {unit.id}. {unit.title}")
        lines.append("")
        lines.append(f"*{unit.summary}* | {sec_count} 节 · {leaf_count} 知识点 | 重要度 {'⭐' * unit.importance}")
        lines.append("")

    (docs_dir / "index.md").write_text("\n".join(lines), encoding="utf-8")


def _generate_mkdocs_yml(
    tree: ExamTree,
    output_dir: Path,
    nav: list,
) -> None:
    """
    生成 mkdocs.yml 配置文件。

    配置要点：
        - Material 主题
        - arithmatex 扩展（KaTeX 渲染 LaTeX）
        - 搜索插件
        - 中文支持
    """
    # mkdocs.yml 的 markdown_extensions 中，arithmatex 需要嵌套配置
    # PyYAML 无法直接表达 "- pymdownx.arithmatex:\n    generic: true" 这种混合列表格式
    # 所以直接手写 YAML 字符串更可控
    import yaml

    # 主配置（不含 markdown_extensions 和 extra_javascript，这两部分手写）
    config = {
        "site_name": f"{tree.exam_name} 知识树",
        "docs_dir": "docs",
        "site_dir": "site",
        "use_directory_urls": False,  # file:// 协议下直接指向 .html 文件
        "theme": {
            "name": "material",
            "language": "zh",
            "palette": [
                {
                    "scheme": "default",
                    "primary": "indigo",
                    "accent": "indigo",
                    "toggle": {
                        "icon": "material/brightness-7",
                        "name": "切换到暗色模式",
                    },
                },
                {
                    "scheme": "slate",
                    "primary": "indigo",
                    "accent": "indigo",
                    "toggle": {
                        "icon": "material/brightness-4",
                        "name": "切换到亮色模式",
                    },
                },
            ],
            "features": [
                "navigation.tabs",
                "navigation.sections",
                "navigation.expand",
                "navigation.top",
                "search.highlight",
                "search.share",
                "content.code.copy",
            ],
        },
        "plugins": [
            "search",
        ],
        "nav": nav,
    }

    yml_path = output_dir / "mkdocs.yml"
    with open(yml_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # 手写 markdown_extensions（arithmatex 需要嵌套的 generic: true）
        f.write("\n# LaTeX 数学公式支持（KaTeX）\n")
        f.write("markdown_extensions:\n")
        f.write("  - pymdownx.arithmatex:\n")
        f.write("      generic: true\n")
        f.write("  - pymdownx.highlight\n")
        f.write("  - pymdownx.superfences\n")
        f.write("  - pymdownx.details\n")
        f.write("  - admonition\n")
        f.write("  - toc:\n")
        f.write("      permalink: true\n")
        f.write("\n")

        # KaTeX CDN + 初始化脚本
        f.write("extra_javascript:\n")
        f.write("  - javascripts/katex.js\n")
        f.write("  - javascripts/tab-scroll.js\n")
        f.write("  - https://unpkg.com/katex@0.16.10/dist/katex.min.js\n")
        f.write("  - https://unpkg.com/katex@0.16.10/dist/contrib/auto-render.min.js\n")
        f.write("\n")
        f.write("extra_css:\n")
        f.write("  - stylesheets/custom.css\n")
        f.write("  - https://unpkg.com/katex@0.16.10/dist/katex.min.css\n")

    # 生成 KaTeX 初始化脚本
    _generate_katex_js(docs_dir=output_dir / "docs")

    # 生成 tab 横向滚动按钮脚本
    _generate_tab_scroll_js(docs_dir=output_dir / "docs")

    # 生成自定义 CSS（修复 footer 布局等 + tab 滚动按钮样式）
    _generate_custom_css(docs_dir=output_dir / "docs")

    console.print(f"  [dim]已生成: {yml_path}[/dim]")


def _generate_katex_js(docs_dir: Path) -> None:
    """
    生成 docs/javascripts/katex.js，用于在页面加载后触发 KaTeX 渲染。

    这个脚本配合 pymdownx.arithmatex 的 generic 模式工作：
    arithmatex 会把 $...$ 包裹的内容输出为 <span class="arithmatex">...</span>，
    然后 KaTeX 的 auto-render 会在页面加载时渲染这些元素。
    """
    js_dir = docs_dir / "javascripts"
    js_dir.mkdir(parents=True, exist_ok=True)

    katex_js = """\
document.addEventListener("DOMContentLoaded", function() {
    if (typeof renderMathInElement !== "undefined") {
        renderMathInElement(document.body, {
            delimiters: [
                {left: "$$", right: "$$", display: true},
                {left: "$", right: "$", display: false},
                {left: "\\\\(", right: "\\\\)", display: false},
                {left: "\\\\[", right: "\\\\]", display: true}
            ],
            throwOnError: false
        });
    }
});
"""
    (js_dir / "katex.js").write_text(katex_js, encoding="utf-8")


def _generate_tab_scroll_js(docs_dir: Path) -> None:
    """
    生成 docs/javascripts/tab-scroll.js，为顶部章节导航栏添加左右滚动箭头按钮。

    MkDocs Material 的 navigation.tabs 在章节较多时会溢出，
    但隐藏了滚动条（scrollbar-width: none），用户难以发现可以滚动。
    本脚本在 tab 栏两端注入三角形箭头按钮，点击后平滑滚动，
    并根据滚动位置自动显示/隐藏箭头。
    """
    js_dir = docs_dir / "javascripts"
    js_dir.mkdir(parents=True, exist_ok=True)

    tab_scroll_js = """\
document.addEventListener("DOMContentLoaded", function () {
    var tabList = document.querySelector(".md-tabs__list");
    if (!tabList) return;

    var tabsContainer = document.querySelector(".md-tabs");
    if (!tabsContainer) return;

    // 滚动步长（每次点击滚动的像素数）
    var SCROLL_STEP = 200;

    // 创建左箭头按钮
    var btnLeft = document.createElement("button");
    btnLeft.className = "md-tabs-scroll md-tabs-scroll--left";
    btnLeft.setAttribute("aria-label", "向左滚动");
    btnLeft.innerHTML = "&#9664;";  // ◀

    // 创建右箭头按钮
    var btnRight = document.createElement("button");
    btnRight.className = "md-tabs-scroll md-tabs-scroll--right";
    btnRight.setAttribute("aria-label", "向右滚动");
    btnRight.innerHTML = "&#9654;";  // ▶

    // 注入到 tabs 容器
    tabsContainer.style.position = "relative";
    tabsContainer.appendChild(btnLeft);
    tabsContainer.appendChild(btnRight);

    // 更新箭头可见性
    function updateArrows() {
        var scrollLeft = tabList.scrollLeft;
        var maxScroll = tabList.scrollWidth - tabList.clientWidth;

        // 左箭头：滚动位置 > 0 时显示
        btnLeft.style.display = scrollLeft > 2 ? "flex" : "none";
        // 右箭头：未滚到最右时显示
        btnRight.style.display = scrollLeft < maxScroll - 2 ? "flex" : "none";
    }

    // 点击事件
    btnLeft.addEventListener("click", function () {
        tabList.scrollBy({ left: -SCROLL_STEP, behavior: "smooth" });
    });
    btnRight.addEventListener("click", function () {
        tabList.scrollBy({ left: SCROLL_STEP, behavior: "smooth" });
    });

    // 监听滚动事件更新箭头
    tabList.addEventListener("scroll", updateArrows);
    // 监听窗口缩放
    window.addEventListener("resize", updateArrows);

    // 初始化
    updateArrows();
});
"""
    (js_dir / "tab-scroll.js").write_text(tab_scroll_js, encoding="utf-8")


def _generate_custom_css(docs_dir: Path) -> None:
    """
    生成 docs/stylesheets/custom.css，修复 MkDocs Material 的布局问题并增强交互。

    包含：
        - 隐藏 footer（file:// 协议下遮挡侧边栏底部）
        - 侧边栏滚动修复（覆盖 height:0 和 overflow:hidden）
        - 侧边栏底部留白
        - 顶部 tab 导航栏滚动箭头按钮样式
    """
    css_dir = docs_dir / "stylesheets"
    css_dir.mkdir(parents=True, exist_ok=True)

    custom_css = """\
/* 隐藏 footer：file:// 协议下 footer 会遮挡侧边栏底部导航条目，
   且 "Made with Material for MkDocs" 对本地知识树无实际用途，直接隐藏 */
.md-footer {
    display: none;
}

/* ── 侧边栏滚动修复 ──
   Material 主题在桌面端设置 .md-sidebar { height: 0 }（依赖 JS 动态计算），
   在移动端设置 .md-sidebar__scrollwrap { overflow: hidden }，
   两者都导致 file:// 协议下侧边栏无法正常滚动。 */

/* 桌面端：设置明确高度，使 scrollwrap 有可滚动的容器边界 */
@media screen and (min-width: 76.25em) {
    .md-sidebar {
        height: calc(100vh - 3.6rem) !important;
    }
}

/* 所有尺寸：强制启用纵向滚动 */
.md-sidebar__scrollwrap {
    overflow-y: auto !important;
}

/* 侧边栏底部留白，确保最后几个导航条目可滚动到可见区域 */
.md-sidebar__inner {
    padding-bottom: 3rem;
}

/* ── 顶部 tab 导航栏滚动箭头按钮 ── */
.md-tabs-scroll {
    position: absolute;
    top: 0;
    width: 2rem;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    border: none;
    cursor: pointer;
    color: rgba(255, 255, 255, 0.9);
    font-size: 0.7rem;
    z-index: 2;
    transition: background-color 0.2s;
    /* 默认继承 tab 栏背景色 */
    background-color: var(--md-primary-fg-color);
}

.md-tabs-scroll:hover {
    background-color: rgba(0, 0, 0, 0.15);
}

.md-tabs-scroll--left {
    left: 0;
    /* 左侧渐隐效果 */
    box-shadow: 4px 0 8px rgba(0, 0, 0, 0.1);
}

.md-tabs-scroll--right {
    right: 0;
    /* 右侧渐隐效果 */
    box-shadow: -4px 0 8px rgba(0, 0, 0, 0.1);
}

/* 暗色模式下箭头按钮适配 */
[data-md-color-scheme="slate"] .md-tabs-scroll {
    background-color: var(--md-primary-fg-color);
    color: rgba(255, 255, 255, 0.9);
}
"""
    (css_dir / "custom.css").write_text(custom_css, encoding="utf-8")


def _run_mkdocs_build(output_dir: Path) -> None:
    """
    在 output_dir 下执行 mkdocs build 生成 site/。

    参数:
        output_dir: 包含 mkdocs.yml 和 docs/ 的目录
    """
    console.print("  [dim]正在执行 mkdocs build...[/dim]")
    try:
        result = subprocess.run(
            ["mkdocs", "build"],
            cwd=str(output_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            console.print(f"  [red]mkdocs build 失败:[/red]")
            if result.stderr:
                # 只打印最后 10 行错误
                err_lines = result.stderr.strip().split("\n")[-10:]
                for line in err_lines:
                    console.print(f"    [dim]{line}[/dim]")
        else:
            site_dir = output_dir / "site"
            console.print(f"  [green]✓ 站点已生成: {site_dir}[/green]")
            index = site_dir / "index.html"
            if index.exists():
                console.print(f"  [dim]首页: {index}[/dim]")
    except FileNotFoundError:
        console.print("  [red]错误: 未找到 mkdocs 命令。请确认已安装: pip install mkdocs-material[/red]")
    except subprocess.TimeoutExpired:
        console.print("  [red]错误: mkdocs build 超时（120秒）[/red]")
