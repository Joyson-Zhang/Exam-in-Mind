# Phase 7 — Markdown + MkDocs 渲染器

---

## 基本信息

| 项目 | 内容 |
|---|---|
| Phase 编号 | 7 |
| 主题 | 单文件 Markdown 渲染 + MkDocs 静态站生成 |
| 开始时间 | 2026-04-12 |
| 结束时间 | 2026-04-12 |
| 实际耗时 | 约 25 分钟（含一次 mkdocs.yml 配置修复） |

---

## 目标回顾

把 tree.json 渲染成 full.md 和 MkDocs 静态站。

---

## 实际完成情况

- [x] `exam_in_mind/renderers/markdown_renderer.py` — `render_full_markdown()`
- [x] `exam_in_mind/renderers/mkdocs_renderer.py` — `render_mkdocs_site()`、mkdocs.yml 生成、KaTeX 初始化脚本
- [x] `exam_in_mind/main.py` — 串联 Step 7/8

**与计划的差异：**

PLAN 中 Step 7 对应 markdown 渲染，Step 8 对应 mkdocs 渲染。两者都在本 Phase 实现，无偏差。

**产出物统计：**
- full.md: 789KB，440,511 字符
- docs/: 457 个 Markdown 文件（含 index 页面）
- site/: 458 个 HTML 页面
- mkdocs.yml: 含 Material 主题 + KaTeX + 搜索 + 完整导航

---

## 关键决策记录

### 决策 1：mkdocs.yml 生成方式——PyYAML 还是手写字符串

- **背景**：mkdocs.yml 中的 `markdown_extensions` 部分需要混合格式：有些扩展是纯字符串（如 `- admonition`），有些需要嵌套配置（如 `- pymdownx.arithmatex:\n    generic: true`）
- **初始做法**：全部用 PyYAML 的 dict 生成
- **问题**：PyYAML 把 `{"pymdownx.arithmatex": {"generic": True}}` 渲染为一个 dict 项，而不是 MkDocs 期望的 "带参数的列表项" 格式。导致 arithmatex 配置实际没有生效
- **最终做法**：主配置用 PyYAML 生成，`markdown_extensions` 和 `extra_javascript` 部分用 `f.write()` 手写
- **理由**：MkDocs 的 YAML 配置格式对 `markdown_extensions` 有特殊的语法要求（列表项带嵌套参数），PyYAML 不能自然表达这种格式。手写这一部分更可靠

### 决策 2：KaTeX 的初始化方式

- **背景**：pymdownx.arithmatex 的 `generic` 模式会把 `$...$` 包裹的内容输出为 HTML 标签，但需要客户端 JS 来实际渲染
- **选择**：生成 `docs/javascripts/katex.js`，在 `DOMContentLoaded` 事件中调用 `renderMathInElement`
- **理由**：这是 MkDocs Material 官方推荐的 KaTeX 集成方式。JS 文件会被 mkdocs build 复制到 site/ 目录

### 决策 3：文件路径中的中文处理

- **背景**：很多知识点标题包含中文（如 "极限的直观概念"），需要决定是否在文件名中保留
- **选择**：`_slugify()` 保留中文字符（`\u4e00-\u9fff` 范围），同时移除其他特殊字符
- **理由**：保留中文让 docs/ 目录的可读性更好，MkDocs 和大多数文件系统都支持 UTF-8 文件名

---

## 遇到的问题与解决过程

### 问题 1：arithmatex 配置位置错误

- **现象**：第一版 mkdocs.yml 中，`generic: true` 被放在 `extra.pymdownx.arithmatex` 下，而不是 `markdown_extensions` 中 `pymdownx.arithmatex` 的嵌套参数
- **分析**：用 PyYAML dict 生成时，`markdown_extensions` 列表中的元素只能是字符串或 dict。而 MkDocs 要求的格式是 `- pymdownx.arithmatex:\n    generic: true`（键值对作为列表项），这在 Python dict 中需要表示为 `{"pymdownx.arithmatex": {"generic": True}}`，但 PyYAML 序列化后变成了一个嵌套 dict 而非 MkDocs 期望的格式
- **解决**：将 `markdown_extensions` 和 `extra_javascript` 部分从 PyYAML 生成改为手写 YAML 字符串。虽然不够优雅，但保证了输出格式正确

### 问题 2：SPEC 缺 run.log

- **现象**：SPEC 第 11 节要求产出物中有 `run.log`，但目前代码没有生成
- **决定**：记录在"给下一个 Phase 的提醒"中，Phase 8 实现

---

## 关键代码片段

### 片段 1：mkdocs.yml 混合生成（PyYAML + 手写）

```python
# 主配置用 PyYAML 生成
with open(yml_path, "w", encoding="utf-8") as f:
    yaml.dump(config, f, ...)
    
    # markdown_extensions 手写（arithmatex 需要嵌套参数）
    f.write("markdown_extensions:\n")
    f.write("  - pymdownx.arithmatex:\n")
    f.write("      generic: true\n")
    ...
```

**为什么这样写：** PyYAML 对 MkDocs 特有的"列表项带参数"格式支持不好，手写更可靠。只影响两个 section，其余配置仍用 PyYAML 保证结构正确。

### 片段 2：KaTeX 初始化脚本

```javascript
document.addEventListener("DOMContentLoaded", function() {
    if (typeof renderMathInElement !== "undefined") {
        renderMathInElement(document.body, {
            delimiters: [
                {left: "$$", right: "$$", display: true},
                {left: "$", right: "$", display: false},
            ],
            throwOnError: false
        });
    }
});
```

**为什么这样写：** `throwOnError: false` 确保单个公式渲染失败不会阻断整个页面。`typeof` 检查防止 KaTeX CDN 加载失败时报错。

---

## 可作为博客素材的亮点

- **PyYAML vs MkDocs YAML 格式冲突**：PyYAML 生成的 YAML 在语法上完全合法，但不符合 MkDocs 对 `markdown_extensions` 的语义要求。这是一个"格式正确但语义错误"的经典案例。
- **产出物规模**：378 个知识点 → 457 个 Markdown 文件 → 458 个 HTML 页面，单文件 full.md 达到 789KB。这展示了 LLM 批量内容生成的产出能力。

---

## 复盘与反思

- mkdocs.yml 的配置问题本应在第一次就发现。如果在写代码时先去看 MkDocs Material 的官方 KaTeX 配置示例，就不会犯这个错
- `_slugify()` 保留中文的决策在 Windows 上可能有路径长度限制的风险（260 字符），但当前知识点标题不长，没有触发
- 如果重来，会先写一个最小的 mkdocs.yml（只含一个页面 + KaTeX 公式），验证渲染后再生成完整站点

---

## 给下一个 Phase 的提醒

- [ ] SPEC 第 11 节要求的 `run.log` 尚未实现，Phase 8 需要加入日志文件输出
- [ ] LaTeX 渲染需要联网加载 KaTeX CDN，SPEC 验收标准说"site/ 完全离线可用"——目前不满足。可以考虑在 Phase 8 中将 KaTeX JS/CSS 下载到 site/ 本地，但这增加了复杂度。建议与用户商讨是否接受 CDN 依赖
- [ ] 验收标准要求"搜索框可搜索关键词"——MkDocs Material 的搜索插件已配置，应该可用，但需要用户在浏览器中实际验证
- [ ] config.yaml 中的模型仍是 Haiku，Phase 8 前决定是否改回 Sonnet
