# AgentGuard — Multi-Agent Workflow Guide

## When to Use Sub-Agents

Use sub-agents for:
- **Parallel exploration**: searching backend + frontend simultaneously
- **Deep research**: codebase-wide audits that would bloat main context
- **Independent tasks**: lint checks, grep sweeps, file discovery

Do NOT use sub-agents for:
- Single file reads or targeted greps (use Glob/Grep directly)
- Tasks that depend on the previous step's output
- Simple edits where you already know the file

## Agent Specializations

### Backend Agent
- Scope: `agentguard-backend/backend/app/`
- Key files: `models/`, `api/`, `services/detection/`, `tasks/`, `schemas/`
- Verify with: `pyright app/` (type check), `curl` endpoints
- Pattern: async handlers, sync Celery tasks, org_id tenant isolation

### Frontend Agent
- Scope: `agentguard-frontend/src/`
- Key files: `app/`, `components/`, `hooks/`, `lib/`, `types/`
- Verify with: `npx tsc --noEmit`
- Pattern: TanStack Query, shared constants from `lib/constants.ts`

### Detection Agent
- Scope: `agentguard-backend/backend/app/services/detection/`
- Key files: `types.py` (shared types + ACTION_MODE_MAP), `registry.py`, `pipeline.py`
- Sync detectors run in-request; async detectors run via Celery
- All detectors must register in `registry.py`

### Security Audit Agent
- Check: org_id filters on all queries, no raw secrets in logs
- Check: no f-string SQL, no hardcoded credentials
- Check: Pydantic validation at API boundary
- Check: no dangerouslySetInnerHTML in frontend

## Coordination Rules

1. **One agent per domain**: don't split a single backend change across agents
2. **Share context upfront**: include file paths and line numbers in prompts
3. **Verify after merge**: after combining agent outputs, run type checks on both stacks
4. **Prefer haiku for exploration**: use sonnet/opus only for complex reasoning

## Model Selection

| Task | Model |
|------|-------|
| File search, grep, quick lookups | haiku |
| Standard coding, reviews | sonnet |
| Architecture, multi-file refactors | opus |
