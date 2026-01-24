# Session Start Skill

**Triggers:** `/start`, `/session-start`, `start session`, beginning of new conversation

## Purpose

Initialize a new working session by verifying tool availability, checking for previous work, and reminding about model selection strategy.

## Workflow

### Step 1: Verify Gemini Connectivity

```
mcp__pal__listmodels()
```

Confirm these models are available:
- ✅ `gemini-3-pro-preview` (aliased as `pro`, `gemini3`)
- ✅ `gemini-2.5-flash` (aliased as `flash`)

#### Error Handling

**If `listmodels` succeeds:** Proceed to Step 2.

**If `listmodels` fails or times out:**
1. Don't block the session - assume standard models (Flash/Pro) are available
2. Flag a warning to the user: "⚠️ Could not verify Gemini connectivity. PAL MCP server may be starting up. Proceeding with assumed model availability."
3. Check terminal output for MCP server errors
4. If PAL tools fail during the session, advise user to restart the MCP server or check `GEMINI_API_KEY` configuration

### Step 2: Check for Previous Work

Read `docs/current-work.md` for any active delegations:

```markdown
Found active delegations:
- Rate limiter implementation (continuation_id: abc123...)
- Status: in_progress

Would you like to:
1. Resume previous work
2. Start fresh
```

### Step 3: Model Selection Reminder

```markdown
## Model Strategy for This Session

| Model | Use For | Cost |
|-------|---------|------|
| gemini-2.5-flash | Routine implementation, docs, refactoring | $ |
| gemini-3-pro-preview | Complex analysis, code review, debugging | $$$ |
| Consensus (multi-model) | Architecture decisions | $$$$ |
| Claude (you) | Orchestration, quality gates, user comms | N/A |

**Distribution Target:** 80% Flash / 15% Pro / 5% Consensus
```

### Step 4: Project Context Reminder

```markdown
## stocks_app Quick Reference

**Critical Constraints:**
- SEC EDGAR: 5 req/s (not 10!)
- Gemini tokens: Cost doubles above 200K
- Always validate SEC response body (empty = graylisting)

**Current Phase:** [Check implementation order in CLAUDE.md]

**Key Files:**
- `core/data/rate_limiter.py` - Token bucket
- `core/data/edgar_client.py` - SEC access
- `core/scoring/piotroski.py` - F-Score
- `core/scoring/altman.py` - Z-Score
```

### Step 5: Set Session Goals

Ask user:
```markdown
What would you like to accomplish this session?

Suggested next steps (from CLAUDE.md implementation order):
1. [ ] Rate limiter implementation
2. [ ] SEC EDGAR client
3. [ ] Piotroski F-Score calculator
4. [ ] Basic CLI commands
```

## Quick Start Commands

After session initialization, user can:
- `/delegate` - Start a new delegated task
- `/check-delegations` - Resume previous work
- `/local-review` - Review uncommitted changes

## Session Health Checks

Run periodically during long sessions:
- Context usage: Keep below 70%
- Continuation_ids: Save to `docs/current-work.md` before session ends
- Cost tracking: Note estimated Gemini costs for user awareness
