# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the `agent-md-wizard` Codex skill — a wizard-based tool that generates or updates repository-level `AGENT.MD` files through a six-round guided Q&A session. The skill auto-detects the repo's language, framework, package manager, and existing conventions, then asks one question group at a time before producing a Chinese `AGENT.MD`.

## Key Scripts

- `skills/agent-md-wizard/scripts/detect_repo_context.py <repo_path>` — Inspects a repository and outputs normalized JSON describing languages, frameworks, package managers, commands (install/dev/build/lint/test), repo topology, and whether an existing `AGENT.MD` is present.
- `skills/agent-md-wizard/scripts/build_agent_md.py --answers <json> --detected <json> --output <path> [--dry-run] [--force]` — Merges wizard answers with detected context to produce the final `AGENT.MD`. Use `--dry-run` to preview output before writing.

Both scripts accept inline JSON or a path to a `.json` file.

## Skill Workflow (Six Rounds)

1. Create vs. update — confirm mode and whether an existing `AGENT.MD`/`AGENTS.md` exists
2. Project shape — application/service/library/full-stack and single-repo vs. monorepo
3. Tech stack — language, framework, package manager, runtime
4. Core commands — install, dev, build, lint, test (use detection to prefill, confirm with user)
5. Coding & review rules — style, review focus, test threshold
6. Risk boundaries — secrets, migrations, dangerous commands, generated files, collaboration

## Repo Detection Capabilities

Supports auto-detection for:
- **Node.js**: detects `package.json`, lockfiles (pnpm/yarn/bun/npm), TypeScript, frameworks (Next.js, React, Vue, NestJS, etc.), and npm script commands
- **Python**: detects `pyproject.toml`, `requirements*.txt`, `setup.py`, uv/Poetry/pip, frameworks (FastAPI, Django, Flask, Streamlit, etc.)
- **Go**: detects `go.mod`, modules, golangci-lint, and frameworks (Gin, Echo, Fiber, Cobra)
- **Rust**: detects `Cargo.toml`, cargo commands, frameworks (Actix, Axum, Rocket, Clap)
- **CI/CD**: scans `.github/workflows/`, `.gitlab-ci.yml`, `Dockerfile` patterns for lint/test/build commands
- **Repo topology**: detects monorepo markers (`pnpm-workspace.yaml`, `turbo.json`, `nx.json`, `go.work`)

## Output Language

Default output is Chinese. The generated `AGENT.MD` sections are:
- 项目背景与适用范围
- 开发工作流与核心命令
- 编码与评审约定
- 测试与验收要求
- 风险控制与禁止事项
- 协作补充说明与仓库特例

## Important Behavioral Notes

- Detection is a starting point, not a final answer — always confirm low-confidence fields with the user
- If `AGENT.MD` already exists, do not overwrite silently — require explicit confirmation before writing
- The skill is invoked with `Use $agent-md-wizard to inspect this repository...` or the Chinese equivalent
