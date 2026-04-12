# Changelog

All notable changes to Exam-in-Mind will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-12

First stable release. First successful end-to-end generation of AP Calculus BC knowledge tree.

### Added
- 命令行工具 `python -m exam_in_mind` 用于自动生成考试知识树
- Brave Search API 集成,通过 Claude custom tool use 查询官方考纲
- 分层知识结构构建(章 → 节 → 知识点 三级)
- 叶子节点内容生成(定义 / 公式 / 易错点)
- LaTeX 数学公式支持(通过 MkDocs arithmatex 扩展)
- 断点续跑与 JSON 缓存机制
- 双格式输出: MkDocs Material 静态站 + 单文件 Markdown
- 完整的中文日志输出和 rich 进度条

### Documentation
- 完整的项目规格文档 (SPEC.md, PLAN.md)
- 项目级 AI 助手行为准则 (CLAUDE.md)
- 8 个 Phase 的开发日志
- 版本开发日志体系

### Verified
- SAT Math smoke test (Haiku, English) - 烟雾测试通过
