# agent-md-wizard

`agent-md-wizard` is a Codex skill for generating or updating a repository-level `AGENT.MD` through a step-by-step wizard.

The skill inspects a repository first, asks one guided question group at a time, previews the generated document, and only writes `AGENT.MD` after confirmation when overwriting may be risky.

## Repository Layout

The publishable skill lives in [skills/agent-md-wizard](skills/agent-md-wizard).

## Install

### Option 1: Manual install

Copy `skills/agent-md-wizard` into your local Codex skills directory:

- Windows: `%USERPROFILE%\\.codex\\skills\\agent-md-wizard`
- macOS/Linux: `~/.codex/skills/agent-md-wizard`

### Option 2: Install from GitHub

If you use the Codex skill installer, install from this repository path:

```bash
python scripts/install-skill-from-github.py --repo isunky/agent-md-wizard --path skills/agent-md-wizard
```

After installation, restart Codex to pick up the new skill.

## Use

Invoke the skill with a prompt like:

```text
Use $agent-md-wizard to inspect this repository, guide me one step at a time, preview the draft, and then write AGENT.MD.
```

## What It Generates

The resulting `AGENT.MD` includes:

- project background and scope
- workflow and core commands
- coding and review conventions
- testing and acceptance expectations
- risk controls and forbidden operations
- collaboration notes and repository-specific rules
