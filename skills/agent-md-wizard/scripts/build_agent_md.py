#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .constants import KIND_LABELS, TOPOLOGY_LABELS
except ImportError:
    from constants import KIND_LABELS, TOPOLOGY_LABELS  # type: ignore


DEFAULT_STYLE_RULES = [
    "优先沿用仓库现有目录结构、命名方式和依赖约定，避免无收益的大范围重构。",
    "先完成最小可验证闭环，再补充必要注释、文档和脚本说明。",
    "优先修复根因，不用表面兜底替代问题分析。",
    "新增依赖、配置或生成物前先确认必要性，并尽量控制影响面。",
]

DEFAULT_REVIEW_FOCUS = [
    "行为回归、兼容性和边界条件。",
    "错误处理、超时重试、资源释放和并发安全。",
    "接口契约、配置变更以及数据迁移影响。",
    "敏感信息、权限边界和危险操作保护。",
]

DEFAULT_DANGEROUS_COMMANDS = [
    "git reset --hard",
    "git checkout --",
    "rm -rf",
    "drop database",
    "terraform destroy",
]


def load_json_arg(value: str):
    stripped = value.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError as e:
            raise SystemExit(f"Invalid inline JSON: {e}") from e
    potential_path = Path(value)
    if potential_path.exists():
        try:
            return json.loads(potential_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise SystemExit(f"Invalid JSON in {potential_path}: {e}") from e
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        raise SystemExit(f"Invalid JSON: neither inline JSON, valid file path, nor valid JSON string: {value[:100]}...")


def _normalize_string(value: str) -> str:
    return value.strip()


def dedupe(items):
    seen = set()
    output = []
    for item in items:
        if item is None:
            continue
        if isinstance(item, str):
            normalized = _normalize_string(item)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            output.append(normalized)
        else:
            if item in seen:
                continue
            seen.add(item)
            output.append(item)
    return output


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if item not in (None, "")]
    if isinstance(value, str):
        stripped = _normalize_string(value)
        return [stripped] if stripped else []
    return [value]


def pick(data, *paths, default=None):
    for path in paths:
        current = data
        ok = True
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                ok = False
                break
        if ok and current not in (None, "", []):
            return current
    return default


def merge_command_values(answer_value, detected_values):
    answer_list = ensure_list(answer_value)
    detected_list = ensure_list(detected_values)
    merged = dedupe(answer_list + detected_list)
    return merged


def format_command_candidates(values):
    values = ensure_list(values)
    if not values:
        return "待补充"
    if len(values) == 1:
        return f"`{values[0]}`"
    primary = values[0]
    alternates = " / ".join(f"`{value}`" for value in values[1:])
    return f"首选 `{primary}`；备选 {alternates}"


def sentence_list(items):
    items = dedupe(ensure_list(items))
    return "、".join(items) if items else "待确认"


def build_project_summary(project_name, kind, topology, languages, frameworks):
    parts = [f"{project_name} 是一个{TOPOLOGY_LABELS.get(topology, topology)}{KIND_LABELS.get(kind, kind)}。"]
    if languages:
        parts.append(f"当前主要语言为 {sentence_list(languages)}。")
    if frameworks:
        parts.append(f"已识别的核心框架包括 {sentence_list(frameworks)}。")
    else:
        parts.append("核心框架仍需结合仓库现状进一步确认。")
    return " ".join(parts)


def format_flat_bullets(items):
    return "\n".join(f"- {item}" for item in dedupe(items))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build AGENT.MD from wizard answers and detected repository context.")
    parser.add_argument("--answers", required=True, help="Path to answers JSON or inline JSON")
    parser.add_argument("--detected", required=True, help="Path to detected JSON or inline JSON")
    parser.add_argument("--output", required=True, help="Path to output markdown file")
    parser.add_argument("--dry-run", action="store_true", help="Print the generated markdown instead of writing it")
    parser.add_argument("--force", action="store_true", help="Allow overwriting an existing output file")
    args = parser.parse_args()

    answers = load_json_arg(args.answers)
    detected = load_json_arg(args.detected)
    output_path = Path(args.output).resolve()

    mode = str(pick(answers, ("mode",), default="create")).strip() or "create"
    project_name = str(
        pick(
            answers,
            ("project_name",),
            ("project", "name"),
            default=output_path.parent.name or "当前项目",
        )
    )
    kind = str(
        pick(
            answers,
            ("project_type",),
            ("project", "type"),
            ("repo_shape", "kind"),
            default=pick(detected, ("repo_shape", "kind"), default="unknown"),
        )
    )
    topology = str(
        pick(
            answers,
            ("repo_topology",),
            ("project", "topology"),
            ("repo_shape", "topology"),
            default=pick(detected, ("repo_shape", "topology"), default="single-repo"),
        )
    )

    languages = dedupe(
        ensure_list(pick(answers, ("languages",), ("project", "languages"), default=[]))
        + ensure_list(detected.get("languages", []))
    )
    frameworks = dedupe(
        ensure_list(pick(answers, ("frameworks",), ("project", "frameworks"), default=[]))
        + ensure_list(detected.get("frameworks", []))
    )
    package_managers = dedupe(
        ensure_list(pick(answers, ("package_managers",), ("project", "package_managers"), default=[]))
        + ensure_list(detected.get("package_managers", []))
    )

    commands = {}
    detected_commands = detected.get("commands", {})
    answer_commands = pick(answers, ("commands",), default={}) or {}
    for category in ("install", "dev", "build", "lint", "test"):
        commands[category] = merge_command_values(
            answer_commands.get(category),
            detected_commands.get(category, []),
        )

    style_rules = dedupe(
        ensure_list(pick(answers, ("standards", "style_rules"), ("style_rules",), default=[]))
        + DEFAULT_STYLE_RULES
    )
    review_focus = dedupe(
        ensure_list(pick(answers, ("standards", "review_focus"), ("review_focus",), default=[]))
        + DEFAULT_REVIEW_FOCUS
    )
    test_threshold = str(
        pick(
            answers,
            ("standards", "test_threshold"),
            ("test_threshold",),
            default="提交前至少运行与改动直接相关的 lint 与测试；若受环境限制无法执行，必须明确说明原因、风险和未验证范围。",
        )
    )

    secrets_rule = str(
        pick(
            answers,
            ("risks", "secrets_rule"),
            ("secrets_rule",),
            default="禁止在代码、日志、截图、示例数据或提交记录中泄露密钥、Token、证书、客户数据和其他敏感信息。",
        )
    )
    migration_rule = str(
        pick(
            answers,
            ("risks", "migration_rule"),
            ("migration_rule",),
            default="涉及数据库迁移、接口契约、配置格式或基础设施调整时，先说明影响范围、回滚方式和验证步骤，再执行变更。",
        )
    )
    generated_files_rule = str(
        pick(
            answers,
            ("risks", "generated_files_rule"),
            ("generated_files_rule",),
            default="生成文件仅在明确需要提交且可复现时入库；否则说明生成来源与再生成方式。",
        )
    )
    collaboration_rule = str(
        pick(
            answers,
            ("risks", "collaboration_rule"),
            ("collaboration_rule",),
            default="默认不覆盖他人未确认的修改；遇到冲突先对齐背景、目标和影响范围，再决定如何合并。",
        )
    )
    dangerous_commands = dedupe(
        ensure_list(pick(answers, ("risks", "dangerous_commands"), ("dangerous_commands",), default=[]))
        + DEFAULT_DANGEROUS_COMMANDS
    )
    extra_notes = dedupe(
        ensure_list(pick(answers, ("special_cases",), default=[]))
        + ensure_list(pick(answers, ("extra_notes",), default=[]))
    )

    if detected.get("has_existing_agent_md"):
        extra_notes.insert(0, "仓库已存在 AGENT.MD 或 AGENTS.md，更新时优先保留已有术语、流程和团队习惯，不静默整份重写。")
    if mode == "update":
        extra_notes.insert(0, "本次任务按更新现有 AGENT.MD 处理，应尽量做增量调整并保留已确认约定。")
    confidence_notes = ensure_list(detected.get("confidence_notes", []))
    if confidence_notes:
        extra_notes.extend([f"待确认项：{note}" for note in confidence_notes])

    project_summary = str(
        pick(
            answers,
            ("project_summary",),
            ("project", "summary"),
            default=build_project_summary(project_name, kind, topology, languages, frameworks),
        )
    )
    project_scope = str(
        pick(
            answers,
            ("project_scope",),
            ("project", "scope"),
            default="适用于仓库根目录及其纳管子目录；若子项目存在独立规范，以子项目文档优先。",
        )
    )
    review_summary = str(
        pick(
            answers,
            ("standards", "review_summary"),
            ("review_summary",),
            default="评审时优先关注是否满足需求、是否引入回归、是否保留可维护性，而不是只看代码是否能运行。",
        )
    )

    markdown = "\n".join(
        [
            "# AGENT.MD",
            "",
            "## 项目背景与适用范围",
            f"- 项目定位：{project_summary}",
            f"- 适用范围：{project_scope}",
            f"- 项目形态：{TOPOLOGY_LABELS.get(topology, topology)} {KIND_LABELS.get(kind, kind)}。",
            f"- 技术栈：语言 {sentence_list(languages)}；框架 {sentence_list(frameworks)}；包管理 {sentence_list(package_managers)}。",
            "",
            "## 开发工作流与核心命令",
            f"- 安装依赖：{format_command_candidates(commands['install'])}",
            f"- 本地开发：{format_command_candidates(commands['dev'])}",
            f"- 构建产物：{format_command_candidates(commands['build'])}",
            f"- 代码检查：{format_command_candidates(commands['lint'])}",
            f"- 测试验证：{format_command_candidates(commands['test'])}",
            "- 修改前先阅读与目标模块直接相关的代码、配置和文档，优先在现有约定中完成需求闭环。",
            "",
            "## 编码与评审约定",
            format_flat_bullets(style_rules),
            f"- 评审重点：{review_summary}",
            *[f"- Review 关注：{item}" for item in review_focus],
            "",
            "## 测试与验收要求",
            f"- 基线要求：{test_threshold}",
            "- 变更说明中要明确已执行的验证、未执行项及原因，避免把隐含风险留给后续协作者。",
            "- 若修改接口、数据结构或关键流程，需要补充对应的回归场景说明。",
            "",
            "## 风险控制与禁止事项",
            f"- 敏感信息：{secrets_rule}",
            f"- 迁移变更：{migration_rule}",
            f"- 生成文件：{generated_files_rule}",
            f"- 协作边界：{collaboration_rule}",
            f"- 禁止默认执行的危险命令：{', '.join(f'`{item}`' for item in dangerous_commands)}。",
            "",
            "## 协作补充说明与仓库特例",
            format_flat_bullets(extra_notes or ["暂无额外特例；如后续出现团队专属流程，请在本节持续补充。"]),
            "",
        ]
    )

    if args.dry_run:
        sys.stdout.write(markdown)
        return 0

    if output_path.exists() and not args.force:
        sys.stderr.write(f"Output file already exists: {output_path}\n")
        sys.stderr.write("Re-run with --force after explicit confirmation.\n")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    sys.stdout.write(f"Wrote AGENT.MD to {output_path}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
