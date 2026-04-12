# Exam-in-Mind 开发日志

本目录采用**双层日志体系**,记录项目的完整开发轨迹。

## 日志体系

### Phase 日志(历史存档)

v1.0.0 开发期间按阶段记录的详细日志,每个 Phase 一个文件。v1.0.0 发布后不再新增,作为历史存档永久保留。

- 模板: `TEMPLATE.md`
- 命名: `phase-{编号}-{简短主题}.md`

### 版本开发日志(日常记录)

v1.0.0 发布后采用的日志格式,按版本号组织,每次 commit 都在对应版本日志中留痕。

- 模板: `VERSION_LOG_TEMPLATE.md`
- 命名: `versions/v{版本号}-dev.md`
- 格式: 三段式(问题/做法/效果),按日期分组

## 目录结构

```
devlog/
├── README.md                    # 本文件
├── TEMPLATE.md                  # Phase 日志模板(历史)
├── VERSION_LOG_TEMPLATE.md      # 版本日志模板(当前)
├── phase-1-scaffolding.md       # Phase 1-8 历史存档
├── phase-2-brave-search.md
├── phase-3-models-cache.md
├── phase-4-outline-builder.md
├── phase-5-tree-builder.md
├── phase-6-content-builder.md
├── phase-7-renderers.md
├── phase-8-integration.md
└── versions/
    ├── v1.0.0-dev.md            # v1.0.0 版本日志(已封版)
    └── v1.0.1-dev.md            # v1.0.1 版本日志(进行中)
```

## Phase 日志索引

| 文件 | Phase | 主题 |
|---|---|---|
| [phase-1-scaffolding.md](phase-1-scaffolding.md) | Phase 1 | 项目脚手架与配置系统 |
| [phase-2-brave-search.md](phase-2-brave-search.md) | Phase 2 | Brave Search 模块与工具封装 |
| [phase-3-models-cache.md](phase-3-models-cache.md) | Phase 3 | 数据模型(Pydantic)与 JSON 缓存 |
| [phase-4-outline-builder.md](phase-4-outline-builder.md) | Phase 4 | LLM 客户端与宏观框架构建器 |
| [phase-5-tree-builder.md](phase-5-tree-builder.md) | Phase 5 | 递归分解器(level=1→2→3) |
| [phase-6-content-builder.md](phase-6-content-builder.md) | Phase 6 | 叶子内容生成器(LeafContent) |
| [phase-7-renderers.md](phase-7-renderers.md) | Phase 7 | Markdown + MkDocs 渲染器 |
| [phase-8-integration.md](phase-8-integration.md) | Phase 8 | 主流程串联 + README + 烟雾测试 |

## 版本日志索引

| 文件 | 版本 | 状态 |
|---|---|---|
| [versions/v1.0.0-dev.md](versions/v1.0.0-dev.md) | v1.0.0 | 已封版 |
| [versions/v1.0.1-dev.md](versions/v1.0.1-dev.md) | v1.0.1 | 进行中 |
