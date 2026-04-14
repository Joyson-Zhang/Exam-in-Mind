# gh-pages — Exam-in-Mind 发布分支

此分支是 GitHub Pages 的发布源,**只存放生成物**,不含任何源码。
源码与开发日志在 [`main` 分支](https://github.com/Joyson-Zhang/Exam-in-Mind)。

在线访问: https://joyson-zhang.github.io/Exam-in-Mind/

## 目录

| 路径 | 内容 |
|---|---|
| `index.html` | 着陆页,列出所有已发布科目 |
| `ap_calculus_bc/` | AP Calculus BC 知识树(MkDocs 静态站) |
| `sat_math/` | SAT Math 知识树(MkDocs 静态站) |
| `.nojekyll` | 禁用 Jekyll,保留 `_` 开头的资源目录 |

## 如何重新发布

在 main 分支重新生成 `output/<slug>/site/` 后,按以下步骤覆盖更新:

```bash
# 1. 切到 gh-pages worktree(第一次需先 git worktree add)
cd ../Exam-in-Mind-pages

# 2. 清掉旧的科目目录
rm -rf ap_calculus_bc sat_math

# 3. 从 main 的 output 复制最新 site
cp -r ../Exam-in-Mind/output/ap_calculus_bc/site ./ap_calculus_bc
cp -r ../Exam-in-Mind/output/sat_math/site       ./sat_math

# 4. 若新增科目,顺手更新 index.html 里的卡片列表

# 5. 提交并推送
git add -A
git commit -m "publish: update <slug>"
git push
```

## 不要做的事

- ❌ 不要 merge main → gh-pages(两个分支 history 隔离,orphan 设计就是为此)
- ❌ 不要在 gh-pages 放源码(源码在 main)
- ❌ 不要手工改 `ap_calculus_bc/` 或 `sat_math/` 里的 HTML(会被下次覆盖)
