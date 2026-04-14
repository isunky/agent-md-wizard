---
name: agent-md-wizard
description: Generate or update a repository-level `AGENT.MD` for AI coding workflows through a step-by-step wizard. Use when Codex needs to inspect a repo, ask one guided question group at a time, collect engineering conventions, and produce a Chinese `AGENT.MD` for new projects or existing repositories that need collaboration rules, commands, testing expectations, and risk boundaries.
---

# Agent Md Wizard

## Overview

Inspect the repository first, then guide the user through a compact six-round wizard. Keep the interaction in Chinese by default, preview the generated `AGENT.MD`, and write the file only after explicit confirmation when an existing file may be replaced.

## Workflow

1. Run `scripts/detect_repo_context.py <repo_path>` before asking questions.
2. Read `references/question-tree.md` and follow the six standard rounds in order.
3. Ask only one group of questions at a time. After each round, reply with a one-sentence summary of what was locked in.
4. Use repository detection to prefill choices and skip only the questions that are already high-confidence.
5. Read `references/content-presets.md` when you need default Chinese wording for project positioning, coding rules, testing policy, or risk controls.
6. Build the draft with `scripts/build_agent_md.py --answers <json> --detected <json> --output <path> --dry-run`.
7. Show the preview, call out any low-confidence fields, and confirm before writing `AGENT.MD`.
8. If the target file already exists, do not overwrite silently. Write only after the user explicitly confirms the update.

## Wizard Rules

- Default target file name to `AGENT.MD` in the repository root.
- Default document language to Chinese.
- Treat repository detection as a starting point, not a final answer. Ask the user to confirm project type, critical commands, testing expectations, and dangerous operations whenever confidence is not high.
- Keep the standard wizard to six rounds:
  - Create vs. update and existing `AGENT.MD`
  - Project shape and topology
  - Main stack and runtime
  - Install, dev, build, lint, and test commands
  - Coding standards, review focus, and test threshold
  - Secrets, migrations, dangerous commands, generated files, and collaboration rules
- Allow short branch questions only when the repository is mixed-language, monorepo-shaped, or missing reliable command signals.

## Generated Document Requirements

- Always include these sections in the final `AGENT.MD`:
  - `项目背景与适用范围`
  - `开发工作流与核心命令`
  - `编码与评审约定`
  - `测试与验收要求`
  - `风险控制与禁止事项`
  - `协作补充说明与仓库特例`
- Prefer explicit commands over abstract prose.
- Preserve repo-specific wording from the user when provided.
- If detection finds an existing `AGENT.MD`, bias toward incremental updates instead of rewriting the tone from scratch.

## Resources

- `scripts/detect_repo_context.py`: Inspect manifests, lockfiles, Docker or CI files, and existing `AGENT.MD` signals. Return normalized JSON only.
- `scripts/build_agent_md.py`: Merge wizard answers with detected context, preview the output, and write the final Markdown.
- `references/question-tree.md`: Canonical wizard rounds, answer keys, and round summaries.
- `references/content-presets.md`: Default Chinese wording for common project types, review policies, testing rules, and risk controls.
