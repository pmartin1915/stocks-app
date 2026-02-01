# Commit Skill

**Triggers:** `/commit`, `commit this`, `commit changes`

## Purpose

Create well-structured git commits following conventional commit format with proper co-authorship attribution.

## Allowed Commands

```
Bash(git add *)
Bash(git commit *)
Bash(git status*)
Bash(git diff*)
Bash(git log*)
```

## Commit Message Format

Use conventional commits with these types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no code change
- `refactor`: Code restructure, no behavior change
- `perf`: Performance improvement
- `test`: Adding/updating tests
- `chore`: Build, config, tooling

### Structure

```
<type>(<scope>): <short summary>

<body - what and why, not how>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

### Rules

1. **Subject line**: Max 50 chars, imperative mood ("add" not "added")
2. **Scope**: Optional, lowercase (cli, scoring, edgar, gemini, db, mcp, dashboard)
3. **Body**: Wrap at 72 chars, explain motivation
4. **No periods** at end of subject line

## Workflow

### Step 1: Review Changes
```bash
git status
git diff --staged
git diff
```

### Step 2: Stage Files
- Stage specific files, not `git add -A`
- Never commit `.env`, credentials, or large binaries
- Review what's being staged

### Step 3: Analyze and Draft
- Determine commit type from changes
- Write concise subject line
- Add body if changes need explanation

### Step 4: Commit
```bash
git commit -m "$(cat <<'EOF'
<type>(<scope>): <subject>

<body>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

### Step 5: Verify
```bash
git log -1 --stat
```

## Examples

### Simple fix
```
fix(cli): resolve undefined ticker variable in decision commands
```

### Feature with body
```
feat(thesis): add conviction field for investment confidence tracking

- Add conviction (1-5 scale) and conviction_rationale fields to Thesis model
- Update thesis create/list/view/update CLI commands
- Display conviction as visual stars (***.. for 3/5)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

### Multiple changes
```
fix: resolve datetime deprecation warnings across CLI commands

Replace datetime.now() with timezone-aware datetime.now(timezone.utc)
in thesis, screen, watchlist, portfolio, and trends modules.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

## What NOT to Commit

- `.env` files or API keys
- `poetry.lock` changes (unless dependency update)
- Large binary files
- IDE config (`.vscode/`, `.idea/`)
- `__pycache__/`, `.pytest_cache/`

## Pre-commit Checklist

- [ ] Tests pass (`poetry run pytest -x`)
- [ ] No secrets in diff
- [ ] Commit message follows format
- [ ] Scope matches changed area
