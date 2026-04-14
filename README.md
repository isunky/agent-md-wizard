# agent-md-wizard

`agent-md-wizard` 是一个面向 Codex 的技能，用来通过“向导式问答”快速生成或更新仓库级别的 `AGENT.MD`。

它会先扫描当前仓库，再按步骤逐轮提问，收集项目形态、技术栈、核心命令、测试要求和协作边界，先预览生成结果，再在需要时写入 `AGENT.MD`。

`agent-md-wizard` is a Codex skill for generating or updating a repository-level `AGENT.MD` through a step-by-step wizard. It inspects the repository first, asks one guided question group at a time, previews the generated document, and only writes `AGENT.MD` after confirmation when overwriting may be risky.

## 适用场景

适合下面这些场景：

- 新项目初始化时，快速补齐 AI 编程协作规范
- 现有项目没有 `AGENT.MD`，希望低成本生成首版文档
- 仓库已经有 `AGENT.MD` 或 `AGENTS.md`，希望按现有规则增量更新
- 团队需要把开发命令、Review 重点、测试门槛和危险操作约束沉淀成统一入口

## 功能特点

- 仓库自动探测：自动识别常见语言、框架、包管理器和 CI 信号
- 向导式提问：每次只收集一组信息，降低认知负担
- 中文优先：默认生成中文 `AGENT.MD`
- 先预览后写入：避免直接覆盖已有文档
- 可扩展：问题树和内容预设拆分到 `references/`，便于后续继续补充团队规范

## 仓库结构

本仓库中可发布的 skill 位于 [skills/agent-md-wizard](skills/agent-md-wizard)。

主要目录说明：

- `skills/agent-md-wizard/SKILL.md`：skill 入口说明与工作流
- `skills/agent-md-wizard/agents/openai.yaml`：UI 元数据
- `skills/agent-md-wizard/scripts/detect_repo_context.py`：仓库上下文探测脚本
- `skills/agent-md-wizard/scripts/build_agent_md.py`：`AGENT.MD` 生成脚本
- `skills/agent-md-wizard/references/question-tree.md`：向导问题树
- `skills/agent-md-wizard/references/content-presets.md`：中文内容预设

## 安装方式

### 方式一：手动安装

将 `skills/agent-md-wizard` 目录复制到本机 Codex 的 skills 目录中：

- Windows: `%USERPROFILE%\\.codex\\skills\\agent-md-wizard`
- macOS/Linux: `~/.codex/skills/agent-md-wizard`

### 方式二：从 GitHub 安装

如果你使用 Codex 自带的 skill installer，可以直接从这个仓库安装：

```bash
python scripts/install-skill-from-github.py --repo isunky/agent-md-wizard --path skills/agent-md-wizard
```

安装完成后，重启 Codex 以加载新 skill。

## 使用方式

你可以直接这样调用：

```text
Use $agent-md-wizard to inspect this repository, guide me one step at a time, preview the draft, and then write AGENT.MD.
```

如果你更习惯中文，也可以直接这样描述：

```text
使用 $agent-md-wizard 扫描当前仓库，分步骤引导我生成一份中文 AGENT.MD，先预览再写入。
```

## 典型流程

skill 默认按下面的流程工作：

1. 扫描仓库，识别语言、框架、包管理器、CI 和现有 `AGENT.MD`
2. 逐轮确认项目类型、仓库结构和技术栈
3. 逐轮确认 install、dev、build、lint、test 等核心命令
4. 补齐编码规范、Review 关注点和测试门槛
5. 补齐密钥、迁移、危险命令、生成文件和协作边界
6. 先输出预览，再决定是否写入仓库根目录的 `AGENT.MD`

## 生成内容

最终生成的 `AGENT.MD` 默认包含这些部分：

- 项目背景与适用范围
- 开发工作流与核心命令
- 编码与评审约定
- 测试与验收要求
- 风险控制与禁止事项
- 协作补充说明与仓库特例

## 适合谁使用

- 研发负责人：快速沉淀团队 AI 协作规范
- 项目维护者：为仓库补齐统一的 AI 编程入口文档
- 普通研发人员：不用手写模板，也能快速生成一份可用的 `AGENT.MD`

## Notes

- The default output file is `AGENT.MD` in the repository root.
- The current version is optimized for Chinese documentation by default.
- If the repository already contains `AGENT.MD` or `AGENTS.md`, the skill is designed to prefer confirmation before overwriting.
