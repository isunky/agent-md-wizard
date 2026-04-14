# Wizard Question Tree

按固定的六轮向导收集信息。每轮只问一组问题，并在用户回答后输出一句简短总结，再进入下一轮。

## 使用方式

1. 先运行 `scripts/detect_repo_context.py <repo_path>`。
2. 用探测结果预填选项，但不要跳过低置信度字段。
3. 回答写入统一的 `answers` JSON，最后交给 `build_agent_md.py`。

## Round 1: 新建还是更新

- 目标：确认任务模式、目标文件、是否已有历史规范。
- 必问内容：
  - 本次是新建还是更新。
  - 根目录是否存在 `AGENT.MD` 或 `AGENTS.md`，若存在是否以其为基线。
- 推荐总结句：
  - `已确认本次按新建/更新流程处理，目标文件为仓库根目录的 AGENT.MD。`
- 对应答案键：
  - `mode`
  - `project_name`
  - `project_scope`

## Round 2: 项目形态

- 目标：锁定项目类型与仓库拓扑。
- 必问内容：
  - 应用、服务、库、全栈中的哪一种最贴近现状。
  - 单仓还是 Monorepo。
- 可选补问：
  - 若检测到多语言或多包结构，确认是否存在主子项目优先级。
- 推荐总结句：
  - `项目形态已锁定为 <type> + <topology>，后续命令和规则按这个边界组织。`
- 对应答案键：
  - `project.type`
  - `project.topology`

## Round 3: 技术栈与运行时

- 目标：确认主要语言、框架、包管理器和关键运行环境。
- 必问内容：
  - 主语言与主框架。
  - 包管理器或构建工具。
  - 是否依赖特定运行时、容器或 CI 流程。
- 推荐总结句：
  - `已确认主技术栈与运行时，后续命令优先围绕这些工具生成。`
- 对应答案键：
  - `project.languages`
  - `project.frameworks`
  - `project.package_managers`
  - `extra_notes`

## Round 4: 核心命令

- 目标：给 `AGENT.MD` 固定写入安装、开发、构建、Lint、测试命令。
- 必问内容：
  - `install`
  - `dev`
  - `build`
  - `lint`
  - `test`
- 处理规则：
  - 若探测结果可信，先展示候选命令让用户确认。
  - 若仓库没有其中某类命令，显式记录为“待补充”或“当前不适用”。
- 推荐总结句：
  - `核心命令已确认，生成文档时会按 install/dev/build/lint/test 五类写入。`
- 对应答案键：
  - `commands.install`
  - `commands.dev`
  - `commands.build`
  - `commands.lint`
  - `commands.test`

## Round 5: 编码与评审规则

- 目标：锁定代码风格、Review 关注点和测试门槛。
- 必问内容：
  - 代码变更是优先小步迭代还是允许较大重构。
  - Review 时最看重什么。
  - 最低测试要求是什么。
- 推荐总结句：
  - `编码与评审规则已锁定，文档会明确写出风格、评审重点和验收门槛。`
- 对应答案键：
  - `standards.style_rules`
  - `standards.review_focus`
  - `standards.review_summary`
  - `standards.test_threshold`

## Round 6: 风险边界

- 目标：补齐密钥、迁移、危险命令、生成文件和协作约束。
- 必问内容：
  - 哪些信息禁止暴露。
  - 哪些变更必须先确认。
  - 哪些命令默认不能执行。
  - 生成文件是否允许提交。
  - 如何处理他人未确认的变更。
- 推荐总结句：
  - `风险边界已确认，AGENT.MD 会明确禁止项和协作保护规则。`
- 对应答案键：
  - `risks.secrets_rule`
  - `risks.migration_rule`
  - `risks.dangerous_commands`
  - `risks.generated_files_rule`
  - `risks.collaboration_rule`

## Minimal Answers JSON

```json
{
  "mode": "create",
  "project": {
    "name": "demo-repo",
    "type": "application",
    "topology": "single-repo",
    "languages": ["TypeScript"],
    "frameworks": ["Next.js"],
    "package_managers": ["pnpm"]
  },
  "commands": {
    "install": "pnpm install",
    "dev": "pnpm dev",
    "build": "pnpm build",
    "lint": "pnpm lint",
    "test": "pnpm test"
  },
  "standards": {
    "style_rules": ["优先沿用现有约定，避免无收益重构。"],
    "review_focus": ["行为回归与边界条件。"],
    "review_summary": "Review 优先关注需求正确性与回归风险。",
    "test_threshold": "提交前至少运行 lint 与测试。"
  },
  "risks": {
    "secrets_rule": "禁止泄露任何密钥与客户数据。",
    "migration_rule": "涉及迁移先说明影响与回滚方案。",
    "dangerous_commands": ["git reset --hard", "rm -rf"],
    "generated_files_rule": "仅在可复现且明确需要时提交生成文件。",
    "collaboration_rule": "默认不覆盖他人未确认的修改。"
  }
}
```
