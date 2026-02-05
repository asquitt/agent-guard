# Workflow Conventions

## Immediate Execution, Not Summarization

When implementing from a plan document:
- Start execution immediately on the next uncompleted session/phase
- Do NOT summarize the plan or ask which session to start
- Just begin the next one

## Scope Discipline

Keep scope tight:
- When asked to build or fix something, implement exactly what's requested before expanding
- Do NOT over-scope into multi-capability rebuilds unless explicitly asked

## Session Checkpoints

For multi-task sessions:
- Focus on ONE deliverable per session with explicit "done when" criteria
- If you finish early, check the plan doc for the next item
- Commit and verify before moving to the next task

## Debugging Structure

When debugging:
- Do NOT explore broadly first
- Start from the error traceback
- Trace the call chain
- Identify root cause before making any changes

Template for debugging prompts:
```
Error: [exact error]
Triggered by: [action]
Likely in: [service/file area]
```

## API Contract-First Development

Before implementing features spanning backend and frontend:
1. Define the Pydantic response model in backend
2. Create the corresponding TypeScript interface in frontend
3. Verify field names, types, and nullability match exactly
4. THEN implement the endpoint and UI against these shared types
