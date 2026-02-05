# Continue Plan Implementation

Automatically continue from the current plan document without summarizing.

## Usage
Run `/continue-plan` to resume implementation from the plan.

## Workflow

1. **Find the plan document**
   - Look for `*-plan.md` or `plan.md` in `docs/` or project root
   - If multiple, use the most recently modified

2. **Identify current progress**
   - Check TODO list for in-progress or pending items
   - Check git log for last completed session/phase
   - Find the next uncompleted session/phase

3. **Begin implementation immediately**
   - Do NOT summarize the plan
   - Do NOT ask which session to start
   - Just start coding the next uncompleted phase

4. **After each session/phase completion**
   - Run type checking: `pyright app/` or `npx tsc --noEmit`
   - Run relevant tests
   - Commit with message: `feat: complete Session X.Y - <description>`

5. **Continue if time remains**
   - Move to the next session automatically
   - Stop only when hitting a blocker or completing all phases

## Template Commit Messages

```
feat: complete Session 2.1 - implement IMAP service integration
feat: complete Session 3.2 - add detection rule engine
fix: resolve Session 4.1 blockers - proxy request handling
```

## If Blocked

- Report the specific blocker clearly
- Suggest 2-3 potential solutions
- Ask for direction only if truly stuck
