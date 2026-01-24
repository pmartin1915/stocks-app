# Check Delegations Skill

**Triggers:** `/check-delegations`, `/resume`, `/continue`, `what was I working on`

## Purpose

Check for active delegations and continuation_ids from previous sessions to seamlessly resume work.

## Workflow

### Step 1: Check Current Work File

Read `docs/current-work.md` for active delegations:

```markdown
# Current Work

## Active Delegations

| Task | continuation_id | Status | Last Updated |
|------|-----------------|--------|--------------|
| Rate limiter implementation | abc123def456 | in_progress | 2025-01-20 |
| F-Score calculator | xyz789... | blocked | 2025-01-19 |
```

### Step 2: Verify Continuation IDs

For each active delegation, verify the continuation_id is still valid by checking if Gemini can resume:

```
mcp__pal__chat(
  prompt: "What is the current status of this task?",
  model: "gemini-2.5-flash",
  continuation_id: "[id from current-work.md]",
  working_directory_absolute_path: "c:\\stocks_app"
)
```

#### Handling Expired/Invalid Continuation IDs

Continuation IDs may expire if:
- The PAL MCP server was restarted
- Too much time has passed (context cache expired)
- The ID was corrupted or incorrectly recorded

**If ID is valid:** Resume normally.

**If ID is expired/invalid (error returned):**
1. Archive the old ID in `docs/current-work.md` (mark status as `expired`)
2. Read the "Last Updated" notes and "Next Step" from current-work.md
3. Start a NEW session with `mcp__pal__chat`:
   ```
   mcp__pal__chat(
     prompt: "Resuming task: [task name]. Previous progress: [summary from current-work.md]. Next step was: [next step]. Please continue from where we left off.",
     model: "gemini-2.5-flash",
     working_directory_absolute_path: "c:\\stocks_app"
   )
   ```
4. Record the NEW continuation_id in `docs/current-work.md`

### Step 3: Present Options to User

```markdown
## Resume Options

1. **Rate limiter implementation** (in_progress)
   - Last activity: 2025-01-20
   - continuation_id: abc123def456
   - Next step: Implement backoff logic

2. **F-Score calculator** (blocked)
   - Last activity: 2025-01-19
   - continuation_id: xyz789...
   - Blocker: Need clarification on ROA calculation

3. **Start new task**
```

### Step 4: Resume Selected Task

When user selects a task to resume:

1. Load the continuation_id
2. Read any related context from previous work
3. Continue with the appropriate PAL tool, passing the continuation_id

## Maintaining Current Work File

### After Starting New Delegation
```markdown
## Active Delegations

| Task | continuation_id | Status | Last Updated |
|------|-----------------|--------|--------------|
| [New Task] | [new_id] | in_progress | [today] |
```

### After Completing Delegation
Move to completed section:
```markdown
## Completed Delegations

| Task | continuation_id | Completed |
|------|-----------------|-----------|
| Rate limiter | abc123... | 2025-01-21 |
```

### After Blocking Issue
Update status:
```markdown
| Task | continuation_id | Status | Last Updated | Blocker |
|------|-----------------|--------|--------------|---------|
| F-Score | xyz789... | blocked | 2025-01-19 | Need ROA clarification |
```

## Session Handoff

At end of session, always:
1. Update `docs/current-work.md` with current state
2. Note any blockers or next steps
3. Return continuation_ids to user for reference

Example session end message:
```
## Session Summary

Completed:
- ✅ Rate limiter basic implementation

In Progress:
- 🔄 Backoff logic (continuation_id: abc123...)

To resume next session:
1. Run `/check-delegations`
2. Or directly: "Continue with abc123..."
```
