# Delegation Session Template

## Session Info

| Field | Value |
|-------|-------|
| **Date** | [YYYY-MM-DD] |
| **Role** | Orchestrator |
| **Mode** | NEW / CONTINUE: [continuation_id] |
| **Primary Task** | [Description] |

---

## Phase 1: PLANNING (Claude)

### Task Analysis
- **Goal:** [What needs to be accomplished]
- **Scope:** [Files/components affected]
- **Constraints:** [SEC limits, token budgets, etc.]

### Subtask Breakdown

| # | Subtask | PAL Tool | Model | Est. Cost |
|---|---------|----------|-------|-----------|
| 1 | [Description] | `mcp__pal__chat` | flash | $0.02 |
| 2 | [Description] | `mcp__pal__thinkdeep` | pro | $0.08 |
| 3 | [Description] | `mcp__pal__codereview` | pro | $0.05 |

**Total Estimated Cost:** $0.15

### User Approval
- [ ] Plan approved by user
- [ ] Cost acceptable
- [ ] Scope confirmed

---

## Phase 2: DELEGATION (Claude → Gemini)

### Subtask 1: [Name]

**Tool:** `mcp__pal__chat`
**Model:** gemini-2.5-flash
**Status:** ⏳ pending / 🔄 in_progress / ✅ complete / ❌ failed

**Prompt:**
```
[Exact prompt sent to Gemini]
```

**Result:**
```
[Summary of Gemini's output]
```

**continuation_id:** `[id returned]`

---

### Subtask 2: [Name]

**Tool:** `mcp__pal__thinkdeep`
**Model:** gemini-3-pro-preview
**Status:** ⏳ pending

**Prompt:**
```
[Exact prompt sent to Gemini]
```

**Result:**
```
[Summary of Gemini's output]
```

**continuation_id:** `[id returned]`

---

## Phase 3: VALIDATION (Claude)

### Quality Gates

| Check | Status | Notes |
|-------|--------|-------|
| Code compiles | ⏳ | |
| Tests pass | ⏳ | |
| SEC rate limit respected | ⏳ | |
| No hardcoded secrets | ⏳ | |
| Gemini review (if critical) | ⏳ | |

### Issues Found
1. [Issue description and resolution]

### Escalations
- [Any tasks that needed Pro after Flash failed]

---

## Phase 4: REPORTING (Claude)

### Session Summary

**Completed:**
- ✅ [Subtask 1]
- ✅ [Subtask 2]

**In Progress:**
- 🔄 [Subtask 3] - continuation_id: `abc123...`

**Blocked:**
- ❌ [Subtask 4] - Blocker: [reason]

### Cost Breakdown

| Model | Tokens | Cost |
|-------|--------|------|
| gemini-2.5-flash | ~5,000 | $0.02 |
| gemini-3-pro-preview | ~10,000 | $0.08 |
| **Total** | | **$0.10** |

### Files Modified
- `core/data/rate_limiter.py` - Created
- `tests/test_rate_limiter.py` - Created

### Next Session

To continue this work:
```
Mode: CONTINUE
continuation_id: [last_id]
Next step: [description]
```

### Handoff Notes
[Any context the next session needs to know]

---

## Quick Reference

### Model Aliases
- `pro` = gemini-3-pro-preview
- `flash` = gemini-2.5-flash

### PAL Tool Mapping
- Simple code → `mcp__pal__chat` + flash
- Complex logic → `mcp__pal__thinkdeep` + pro
- Bug hunting → `mcp__pal__debug` + pro
- Code review → `mcp__pal__codereview` + pro
- Architecture → `mcp__pal__consensus` + multiple

### Domain Reminders
- SEC: 5 req/s, validate response body
- Gemini: Cache for multi-query, watch 200K threshold
- Financial calcs: Always get Pro review
