# Local Review Skill

**Triggers:** `/local-review`, `/code-review`, `/review`, `review my changes`, `review this code`

## Purpose

Perform thorough, senior-engineer-level code review on uncommitted changes before pushing. Optionally get Gemini second opinion for critical code paths.

## Workflow

### Step 1: Gather Changes
```bash
git diff          # Unstaged changes
git diff --staged # Staged changes
git status        # Overview of all changes
```

### Step 2: Systematic Review Checklist

#### Edge Cases
- [ ] Null/undefined inputs handled
- [ ] Empty arrays/collections handled
- [ ] Boundary values (0, -1, MAX_INT)
- [ ] Unicode/special characters in strings
- [ ] Race conditions in async code
- [ ] Network failures and timeouts

#### Security
- [ ] Input validation at boundaries
- [ ] No SQL/command injection vulnerabilities
- [ ] Sensitive data not logged or exposed
- [ ] API keys not hardcoded
- [ ] Auth/authz checks in place

#### Testing
- [ ] New code has test coverage
- [ ] Edge cases have tests
- [ ] Mocks are appropriate (not over-mocked)
- [ ] Tests are deterministic

#### Correctness
- [ ] Logic matches comments/docstrings
- [ ] No off-by-one errors
- [ ] Correct operator precedence
- [ ] Proper error propagation

#### Maintainability
- [ ] No magic numbers (use constants)
- [ ] No unnecessary duplication
- [ ] Clear, descriptive naming
- [ ] Appropriate abstraction level

### Step 3: Financial Domain Checks (stocks_app specific)

#### SEC EDGAR Compliance
- [ ] Rate limiter used for all SEC requests
- [ ] Empty response body validation (graylisting detection)
- [ ] User-Agent header set correctly
- [ ] Bulk data used where possible (zero API calls)

#### Financial Calculations
- [ ] Piotroski F-Score: All 9 criteria correctly implemented
- [ ] Altman Z-Score: Correct coefficients and formula
- [ ] XBRL parsing: Standard tags extracted, custom tags flagged

#### Gemini API Usage
- [ ] Context caching enabled for multi-query sessions
- [ ] Token count checked before API call (200K threshold)
- [ ] Flash used for simple queries, Pro for analysis

### Step 4: Gemini Second Opinion (Optional)

For critical code paths (financial calculations, security, API integrations), invoke Gemini for additional review:

```
mcp__pal__codereview(
  step: "Review the following changes for [specific concern]...",
  step_number: 1,
  total_steps: 2,
  next_step_required: true,
  findings: "[Your initial findings]",
  model: "gemini-3-pro-preview",
  relevant_files: ["path/to/changed/files"],
  review_type: "full"  # or "security", "performance"
)
```

### Step 4b: Security Audit (For Sensitive Components)

When changes touch security-sensitive code, run a dedicated security audit:

**Trigger security audit when modifying:**
- Rate limiter (`core/data/rate_limiter.py`)
- SEC EDGAR client (`core/data/edgar_client.py`)
- API key handling or environment variables
- Authentication/authorization logic
- Input validation at API boundaries

```
mcp__pal__secaudit(
  step: "Security audit of [component] changes. Checking for: input validation, rate limit bypass, credential exposure, injection vulnerabilities.",
  step_number: 1,
  total_steps: 2,
  next_step_required: true,
  findings: "[Your initial security findings]",
  model: "gemini-3-pro-preview",
  relevant_files: ["path/to/security-sensitive/files"],
  audit_focus: "comprehensive",
  threat_level: "medium"  # or "high" for financial/PII handling
)
```

### Step 5: Report Findings

Format findings as:

```markdown
## Code Review: [Date]

### Summary
[1-2 sentence overview]

### Issues Found
1. **[CRITICAL/HIGH/MEDIUM/LOW]** [File:Line] - [Description]
2. ...

### Recommendations
- [Actionable improvement]
- ...

### Gemini Second Opinion
[If invoked, summarize Gemini's additional findings]
```

## When to Invoke Gemini Second Opinion

**Always** for:
- Financial calculation logic (F-Score, Z-Score, XBRL)
- SEC EDGAR client changes
- Rate limiter modifications
- API key handling

**Optional** for:
- CLI command changes
- Documentation updates
- Test modifications
- Styling/formatting

## Output Location

Save comprehensive reviews to `docs/CODE_REVIEW_[DATE].md` for future reference.
