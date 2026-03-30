---
name: summarize-pr
description: 查看当前分支与主分支的差异，用简体中文给出一份面向非技术团队成员的高层次 PR 摘要。
---

# Summarize PR

用简体中文为非技术团队成员生成当前 PR 的高层次摘要。

## Step 1 — 确定基准分支

1. 运行 `git rev-parse --abbrev-ref HEAD` 获取当前分支名。
2. 尝试检测基准分支：先检查是否有关联的 PR（`gh pr view --json baseRefName -q .baseRefName`），如果有则使用 PR 的 base branch；否则依次尝试 `main`、`master` 作为基准分支。
3. 如果 `$ARGUMENTS` 提供了 PR 编号，则使用 `gh pr view <number> --json baseRefName,headRefName` 获取对应分支信息。

## Step 2 — 收集变更信息

1. 运行 `git log --oneline <base>..HEAD` 查看所有 commit 列表。
2. 运行 `git diff <base>...HEAD --stat` 查看文件变更概览。
3. 运行 `git diff <base>...HEAD` 查看完整 diff（如果 diff 过大，优先关注非测试、非生成的核心文件）。
4. 如果有关联的 PR，运行 `gh pr view --json title,body` 获取 PR 标题和描述作为额外上下文。

## Step 3 — 生成摘要

用简体中文输出以下格式的摘要：

```
## 一句话概括

<用一句通俗的话说明这个 PR 做了什么>

## 主要改动

- <改动点 1：用通俗易懂的语言描述，避免技术术语>
- <改动点 2>
- ...

## 对用户/产品的影响

- <影响 1（如有）>
- <影响 2>

如果没有用户可感知的影响，写"本次改动为内部优化，用户无感知变化。"
```

## Rules

- 所有输出必须使用简体中文。
- 语气简洁友好，让非技术人员（产品、设计、运营）也能快速理解。
- 避免技术术语（如 refactor、middleware、hook、state）。如果必须提及技术概念，用括号附上通俗解释。
- 合并相关的小改动为一条，不要逐文件列举。
- 重点说明"做了什么"和"为什么"，而不是"改了哪些文件"。
- 如果 diff 包含多个不相关的改动，按主题分组说明。
