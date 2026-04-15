#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    from .constants import KIND_LABELS, TOPOLOGY_LABELS
except ImportError:
    from constants import KIND_LABELS, TOPOLOGY_LABELS  # type: ignore

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
    ".nuxt",
    ".turbo",
    ".cache",
    "target",
    "vendor",
    "__pycache__",
}

EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
}

NODE_FRAMEWORKS = {
    "next": "Next.js",
    "react": "React",
    "vue": "Vue",
    "nuxt": "Nuxt",
    "svelte": "Svelte",
    "astro": "Astro",
    "vite": "Vite",
    "express": "Express",
    "@nestjs/core": "NestJS",
    "koa": "Koa",
    "fastify": "Fastify",
    "electron": "Electron",
}

PYTHON_FRAMEWORKS = {
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "streamlit": "Streamlit",
    "typer": "Typer",
    "gradio": "Gradio",
}

GO_FRAMEWORKS = {
    "github.com/gin-gonic/gin": "Gin",
    "github.com/labstack/echo": "Echo",
    "github.com/gofiber/fiber": "Fiber",
    "github.com/spf13/cobra": "Cobra",
}

RUST_FRAMEWORKS = {
    "actix-web": "Actix Web",
    "axum": "Axum",
    "rocket": "Rocket",
    "clap": "Clap",
}

CI_PATTERNS = {
    "lint": [
        ("pnpm lint", "pnpm lint"),
        ("npm run lint", "npm run lint"),
        ("yarn lint", "yarn lint"),
        ("bun run lint", "bun run lint"),
        ("ruff check", "ruff check ."),
        ("flake8", "flake8 ."),
        ("cargo clippy", "cargo clippy --all-targets --all-features"),
        ("golangci-lint run", "golangci-lint run"),
    ],
    "test": [
        ("pnpm test", "pnpm test"),
        ("npm test", "npm test"),
        ("yarn test", "yarn test"),
        ("bun test", "bun test"),
        ("pytest", "pytest"),
        ("cargo test", "cargo test"),
        ("go test ./...", "go test ./..."),
    ],
    "build": [
        ("pnpm build", "pnpm build"),
        ("npm run build", "npm run build"),
        ("yarn build", "yarn build"),
        ("bun run build", "bun run build"),
        ("cargo build", "cargo build"),
        ("go build ./...", "go build ./..."),
        ("python -m build", "python -m build"),
    ],
}


def unique_append(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def normalize_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        raise RuntimeError(f"Failed to read {path}: {e}") from e


def iter_repo_files(root: Path):
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in SKIP_DIRS and not dirname.startswith(".pytest_cache")
        ]
        current_path = Path(current_root)
        for filename in filenames:
            file_path = current_path / filename
            if os.path.islink(file_path):
                continue
            yield file_path


def load_json(path: Path) -> dict:
    try:
        return json.loads(normalize_text(path))
    except (json.JSONDecodeError, RuntimeError) as e:
        raise RuntimeError(f"Failed to parse JSON from {path}: {e}") from e


def load_toml(path: Path) -> dict:
    raw = path.read_bytes()
    if tomllib is None:
        return {}
    try:
        return tomllib.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return {}


def detect_node(root: Path, files: list[Path], result: dict) -> None:
    package_files = [path for path in files if path.name == "package.json"]
    if not package_files:
        return

    unique_append(result["languages"], "JavaScript")

    node_lockfiles = {path.name for path in files}
    if "pnpm-lock.yaml" in node_lockfiles:
        unique_append(result["package_managers"], "pnpm")
    if "yarn.lock" in node_lockfiles:
        unique_append(result["package_managers"], "yarn")
    if "bun.lock" in node_lockfiles or "bun.lockb" in node_lockfiles:
        unique_append(result["package_managers"], "bun")
    if "package-lock.json" in node_lockfiles or "npm-shrinkwrap.json" in node_lockfiles:
        unique_append(result["package_managers"], "npm")

    scripts_by_name: dict[str, list[str]] = {}
    dependency_names: set[str] = set()
    library_like = False

    for package_file in package_files:
        package_data = load_json(package_file)
        package_manager = str(package_data.get("packageManager", "")).strip()
        if package_manager.startswith("pnpm"):
            unique_append(result["package_managers"], "pnpm")
        elif package_manager.startswith("yarn"):
            unique_append(result["package_managers"], "yarn")
        elif package_manager.startswith("bun"):
            unique_append(result["package_managers"], "bun")
        elif package_manager.startswith("npm"):
            unique_append(result["package_managers"], "npm")

        dependencies = {}
        for key in ("dependencies", "devDependencies", "peerDependencies"):
            dependencies.update(package_data.get(key, {}))
        dependency_names.update(dependencies.keys())

        scripts = package_data.get("scripts", {})
        for name, command in scripts.items():
            if isinstance(command, str):
                scripts_by_name.setdefault(name, []).append(command)

        if any(field in package_data for field in ("main", "module", "exports", "types")):
            library_like = True

    if "typescript" in dependency_names or any(path.suffix in {".ts", ".tsx"} for path in files):
        unique_append(result["languages"], "TypeScript")

    for dependency_name, framework_name in NODE_FRAMEWORKS.items():
        if dependency_name in dependency_names:
            unique_append(result["frameworks"], framework_name)

    if not result["package_managers"]:
        unique_append(result["package_managers"], "npm")
        unique_append(result["confidence_notes"], "未发现 Node 锁文件，暂以 npm 作为默认候选。")

    runner = {
        "pnpm": ("pnpm install", "pnpm"),
        "yarn": ("yarn install", "yarn"),
        "bun": ("bun install", "bun run"),
        "npm": ("npm install", "npm run"),
    }

    primary_manager = result["package_managers"][0]
    install_command, run_prefix = runner.get(primary_manager, ("npm install", "npm run"))
    unique_append(result["commands"]["install"], install_command)

    mapping = {
        "dev": ["dev", "start", "serve"],
        "build": ["build"],
        "lint": ["lint", "check"],
        "test": ["test", "test:unit", "test:ci"],
    }
    for category, script_names in mapping.items():
        for script_name in script_names:
            if script_name in scripts_by_name:
                unique_append(result["commands"][category], f"{run_prefix} {script_name}")

    if library_like and not result["commands"]["dev"]:
        unique_append(result["confidence_notes"], "package.json 更像可发布包，项目类型可能是库。")


def parse_python_dependency_names(pyproject_text: str, requirements_texts: list[str]) -> set[str]:
    names: set[str] = set()
    for line in pyproject_text.splitlines():
        match = re.search(r'["\']([a-zA-Z0-9_.-]+)', line)
        if match:
            names.add(match.group(1).lower())
    for text in requirements_texts:
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name = re.split(r"[<>=!~\[]", line, maxsplit=1)[0].strip().lower()
            if name:
                names.add(name)
    return names


def detect_python(root: Path, files: list[Path], result: dict) -> None:
    pyproject = root / "pyproject.toml"
    requirement_files = [path for path in files if path.name.startswith("requirements") and path.suffix == ".txt"]
    setup_py = root / "setup.py"

    if not pyproject.exists() and not requirement_files and not setup_py.exists():
        return

    unique_append(result["languages"], "Python")
    pyproject_text = normalize_text(pyproject) if pyproject.exists() else ""
    requirement_texts = [normalize_text(path) for path in requirement_files]
    dependency_names = parse_python_dependency_names(pyproject_text, requirement_texts)
    pyproject_data = load_toml(pyproject) if pyproject.exists() else {}

    if pyproject.exists() and ("tool" in pyproject_data and "uv" in pyproject_data["tool"] or (root / "uv.lock").exists()):
        unique_append(result["package_managers"], "uv")
    if pyproject.exists() and ("tool" in pyproject_data and "poetry" in pyproject_data["tool"] or (root / "poetry.lock").exists()):
        unique_append(result["package_managers"], "poetry")
    if requirement_files or setup_py.exists() or pyproject.exists():
        unique_append(result["package_managers"], "pip")

    for dependency_name, framework_name in PYTHON_FRAMEWORKS.items():
        if dependency_name in dependency_names or dependency_name.lower() in pyproject_text.lower():
            unique_append(result["frameworks"], framework_name)

    if "uv" in result["package_managers"]:
        unique_append(result["commands"]["install"], "uv sync")
    elif "poetry" in result["package_managers"]:
        unique_append(result["commands"]["install"], "poetry install")
    elif requirement_files:
        unique_append(result["commands"]["install"], "pip install -r requirements.txt")
    else:
        unique_append(result["commands"]["install"], "pip install -e .")
        unique_append(result["confidence_notes"], "Python 安装命令基于常见包项目约定推断，建议确认。")

    if "pytest" in dependency_names:
        unique_append(result["commands"]["test"], "pytest")
    if "ruff" in dependency_names:
        unique_append(result["commands"]["lint"], "ruff check .")
    elif "flake8" in dependency_names:
        unique_append(result["commands"]["lint"], "flake8 .")
    elif "pylint" in dependency_names:
        unique_append(result["commands"]["lint"], "pylint .")

    if pyproject_text:
        if "[build-system]" in pyproject_text:
            unique_append(result["commands"]["build"], "python -m build")
        if "streamlit" in pyproject_text.lower():
            unique_append(result["commands"]["dev"], "streamlit run app.py")
            unique_append(result["confidence_notes"], "检测到 Streamlit 依赖，开发启动命令使用通用入口 app.py 作为候选。")
        elif "fastapi" in pyproject_text.lower():
            unique_append(result["commands"]["dev"], "uvicorn main:app --reload")
            unique_append(result["confidence_notes"], "检测到 FastAPI，已推断启动命令为 uvicorn main:app --reload；若入口模块不同请更正。")


def detect_go(root: Path, files: list[Path], result: dict) -> None:
    go_mod = root / "go.mod"
    if not go_mod.exists():
        return

    unique_append(result["languages"], "Go")
    unique_append(result["package_managers"], "go modules")
    unique_append(result["commands"]["install"], "go mod download")
    unique_append(result["commands"]["build"], "go build ./...")
    unique_append(result["commands"]["test"], "go test ./...")

    if (root / ".golangci.yml").exists() or (root / ".golangci.yaml").exists():
        unique_append(result["commands"]["lint"], "golangci-lint run")

    go_mod_text = normalize_text(go_mod)
    for module_name, framework_name in GO_FRAMEWORKS.items():
        if module_name in go_mod_text:
            unique_append(result["frameworks"], framework_name)


def detect_rust(root: Path, files: list[Path], result: dict) -> None:
    cargo_toml = root / "Cargo.toml"
    if not cargo_toml.exists():
        return

    unique_append(result["languages"], "Rust")
    unique_append(result["package_managers"], "cargo")
    unique_append(result["commands"]["install"], "cargo fetch")
    unique_append(result["commands"]["build"], "cargo build")
    unique_append(result["commands"]["lint"], "cargo clippy --all-targets --all-features")
    unique_append(result["commands"]["test"], "cargo test")

    cargo_text = normalize_text(cargo_toml)
    for dependency_name, framework_name in RUST_FRAMEWORKS.items():
        if dependency_name in cargo_text:
            unique_append(result["frameworks"], framework_name)


def detect_ci_and_docker(root: Path, files: list[Path], result: dict) -> None:
    docker_files = [
        path
        for path in files
        if path.name == "Dockerfile" or path.name.startswith("Dockerfile.") or path.name.startswith("docker-compose")
    ]
    if docker_files:
        unique_append(result["confidence_notes"], "检测到 Docker 相关文件，可在 AGENT.MD 中补充镜像或容器工作流。")

    workflow_files = [
        path
        for path in files
        if (".github" in path.parts and path.suffix in {".yml", ".yaml"})
        or path.name in {".gitlab-ci.yml", "gitlab-ci.yml"}
    ]
    if not workflow_files:
        return

    unique_append(result["confidence_notes"], "检测到 CI 配置，可优先参考流水线中的构建和测试命令。")
    ci_text = "\n".join(normalize_text(path).lower() for path in workflow_files)
    for category, patterns in CI_PATTERNS.items():
        for needle, command in patterns:
            if re.search(rf"(?<![a-z]){re.escape(needle)}(?![a-z])", ci_text):
                unique_append(result["commands"][category], command)


def detect_repo_shape(root: Path, files: list[Path], result: dict) -> None:
    multiple_package_roots = {
        path.parent for path in files if path.name in {"package.json", "pyproject.toml", "go.mod", "Cargo.toml"}
    }
    topology = "single-repo"
    if any((root / marker).exists() for marker in ("pnpm-workspace.yaml", "turbo.json", "nx.json", "go.work")):
        topology = "monorepo"
    elif len(multiple_package_roots) > 1:
        topology = "monorepo"

    frontend_markers = {"React", "Next.js", "Vue", "Nuxt", "Svelte", "Astro", "Vite"}
    backend_markers = {
        "Express",
        "NestJS",
        "Koa",
        "Fastify",
        "FastAPI",
        "Django",
        "Flask",
        "Gin",
        "Echo",
        "Fiber",
        "Actix Web",
        "Axum",
        "Rocket",
    }

    has_frontend = any(name in frontend_markers for name in result["frameworks"])
    has_backend = any(name in backend_markers for name in result["frameworks"])

    kind = "unknown"
    if has_frontend and has_backend:
        kind = "full-stack"
    elif has_backend:
        kind = "service"
    elif has_frontend:
        kind = "application"
    elif result["commands"]["build"] and result["commands"]["test"] and not result["commands"]["dev"]:
        kind = "library"
        unique_append(result["confidence_notes"], "根据命令信号推测该仓库更像库项目，请向用户确认。")

    if topology == "monorepo":
        sub_package_files = [
            path.parent for path in files
            if path.name in {"package.json", "pyproject.toml", "go.mod", "Cargo.toml"}
            and path.parent != root
        ]
        if sub_package_files:
            unique_append(
                result["confidence_notes"],
                f"检测到 monorepo 结构（含 {len(sub_package_files)} 个子包），"
                "各子包可能有独立命令，根目录命令可能为 workspace 级别过滤命令（如 pnpm --filter pkg dev），"
                "请在向导中确认实际使用的命令是否需要按包拆分。",
            )

    result["repo_shape"] = {
        "kind": kind,
        "topology": topology,
        "summary": f"{TOPOLOGY_LABELS.get(topology, topology)} {KIND_LABELS.get(kind, kind)}",
    }


def detect_existing_agent_md(root: Path, result: dict) -> None:
    has_agent = (root / "AGENT.MD").exists()
    has_agents = (root / "AGENTS.md").exists()
    result["has_existing_agent_md"] = has_agent or has_agents
    if has_agent:
        unique_append(result["confidence_notes"], "仓库根目录已存在 AGENT.MD，默认应走更新流程。")
    elif has_agents:
        unique_append(result["confidence_notes"], "仓库存在 AGENTS.md，建议确认是否需要合并或改名。")


def detect_languages_from_extensions(files: list[Path], result: dict) -> None:
    counts: dict[str, int] = {}
    for path in files:
        language = EXTENSION_LANGUAGE_MAP.get(path.suffix.lower())
        if language:
            counts[language] = counts.get(language, 0) + 1

    for language in sorted(counts):
        if counts[language] >= 2:
            unique_append(result["languages"], language)


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect repository context for AGENT.MD generation.")
    parser.add_argument("repo_path", help="Repository path to inspect")
    args = parser.parse_args()

    root = Path(args.repo_path).resolve()
    if not root.exists() or not root.is_dir():
        print(json.dumps({"error": f"Repository path not found: {root}"}, ensure_ascii=False, indent=2))
        return 1

    files = list(iter_repo_files(root))
    result = {
        "languages": [],
        "frameworks": [],
        "package_managers": [],
        "commands": {
            "install": [],
            "dev": [],
            "build": [],
            "lint": [],
            "test": [],
        },
        "repo_shape": {
            "kind": "unknown",
            "topology": "single-repo",
            "summary": "单仓 待确认项目",
        },
        "has_existing_agent_md": False,
        "confidence_notes": [],
    }

    detect_languages_from_extensions(files, result)
    detect_node(root, files, result)
    detect_python(root, files, result)
    detect_go(root, files, result)
    detect_rust(root, files, result)
    detect_ci_and_docker(root, files, result)
    detect_existing_agent_md(root, result)
    detect_repo_shape(root, files, result)

    if not result["languages"]:
        unique_append(
            result["confidence_notes"],
            "未检测到明确技术栈（支持 Node.js/Python/Go/Rust），"
            "请在向导中显式告知语言、框架及包管理器（如 Java/Maven、.NET/C#、PHP/Composer、Ruby/Bundler 等）。",
        )

    for category, commands in result["commands"].items():
        if not commands:
            unique_append(result["confidence_notes"], f"未可靠识别 {category} 命令，向导中需要人工确认。")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
