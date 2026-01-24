# Delegate Plan Skill

**Triggers:** `/delegate`, `/delegate-plan`, `delegate this task`

## Purpose

Routes tasks to appropriate MCP PAL tools and Gemini models for cost-effective execution while Claude maintains orchestration control.

## Model Selection Strategy

| Task Type | PAL Tool | Model | Cost Tier |
|-----------|----------|-------|-----------|
| Simple implementation | `mcp__pal__chat` | gemini-2.5-flash | $ |
| Complex features | `mcp__pal__thinkdeep` | gemini-3-pro-preview | $$$ |
| Bug investigation | `mcp__pal__debug` | gemini-3-pro-preview | $$$ |
| Code review | `mcp__pal__codereview` | gemini-3-pro-preview | $$$ |
| Plan auditing | `mcp__pal__planner` | gemini-3-pro-preview | $$$ |
| Refactoring | `mcp__pal__refactor` | gemini-2.5-flash | $ |
| Architecture decisions | `mcp__pal__consensus` | pro + flash | $$$$ |
| SEC/Financial logic | `mcp__pal__secaudit` | gemini-3-pro-preview | $$$ |
| Documentation | `mcp__pal__docgen` | gemini-2.5-flash | $ |
| Codebase analysis | `mcp__pal__analyze` | gemini-3-pro-preview | $$$ |
| Test generation | `mcp__pal__testgen` | gemini-3-pro-preview | $$$ |
| Code flow tracing | `mcp__pal__tracer` | gemini-3-pro-preview | $$$ |
| Pre-commit validation | `mcp__pal__precommit` | gemini-3-pro-preview | $$$ |
| Session handoff | `mcp__pal__handoff` | gemini-2.5-flash | $ |

## Distribution Target

- **80%** gemini-2.5-flash (routine work)
- **15%** gemini-3-pro-preview (complex analysis)
- **5%** consensus/multi-model (architecture decisions)

## Workflow

### Phase 1: PLANNING (Claude)
1. Understand the task requirements
2. Break down into subtasks
3. Assign each subtask to appropriate PAL tool + model
4. Present plan to user for approval

### Phase 2: DELEGATION (Claude → Gemini)
1. Execute each subtask via appropriate MCP PAL tool
2. Always pass `continuation_id` to maintain context across calls
3. Use `model` parameter explicitly (e.g., `model: "gemini-2.5-flash"`)

### Phase 3: VALIDATION (Claude)
1. Review each subtask output
2. Run tests if applicable
3. Escalate to Pro model if Flash output is insufficient

### Phase 4: REPORTING (Claude)
1. Summarize completed work
2. Return `continuation_id` for future sessions
3. Update `docs/current-work.md` with progress

## Example Delegation Call

```
mcp__pal__chat(
  prompt: "Implement the token bucket rate limiter for SEC EDGAR requests...",
  model: "gemini-2.5-flash",
  working_directory_absolute_path: "c:\\stocks_app",
  continuation_id: "abc123..."  # Reuse from previous call if continuing
)
```

## Financial Domain Considerations

When delegating tasks related to:
- **SEC EDGAR API**: Remind about 5 req/s rate limit, empty response validation
- **Piotroski/Altman scoring**: Request verification of calculation logic
- **XBRL parsing**: Use Pro model for custom tag handling
- **Gemini API calls**: Remind about 200K token pricing cliff

## Escalation Rules

Escalate from Flash to Pro when:
1. Flash output contains errors or incomplete logic
2. Task involves complex financial calculations
3. Security-sensitive code (API keys, rate limiting)
4. Architecture decisions affecting multiple components
