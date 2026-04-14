# Exam-in-Mind 开发日志

本目录记录项目的开发轨迹,采用**双层日志体系**。

## 当前:版本开发日志

v1.0.0 发布之后进入迭代期,所有开发活动的日志都写在 `versions/v{版本号}-dev.md`。每次 commit 都在对应版本日志中留痕(规则详见 `../CLAUDE.md` §📝 开发日志规则)。

- 当前版本日志路径:`versions/v{当前版本}-dev.md`
- 模板:`VERSION_LOG_TEMPLATE.md`
- 格式:三段式(问题 / 做法 / 效果),按日期分组

## 历史:Phase 日志(只读存档)

`phase-{编号}-{主题}.md` 是 v1.0.0 建造期的详细复盘,每个 Phase 一个文件。v1.0.0 发布后**不再新增**,现有文件作为历史存档永久保留、不再修改。

对应的 Phase 日志模板(已停用)归档在 `../archive/devlog-TEMPLATE.phase.md`。

## 目录一览

```
devlog/
├── README.md                    # 本文件
├── VERSION_LOG_TEMPLATE.md      # 版本日志模板(当前在用)
├── phase-1~8-*.md               # 建造期 Phase 日志(历史存档)
└── versions/
    ├── v1.0.0-dev.md            # 已封版
    └── v{当前}-dev.md           # 进行中
```
