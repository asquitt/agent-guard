# Parallel Review Agents

Spawn focused review agents to audit completed work for bugs and integration issues.

## Usage
Run `/parallel-review` after completing an implementation phase.

## Standard Review Agents (spawn all 4)

### Agent 1: Import & Path Audit
```
Check all new/modified files for:
- Valid import paths (modules actually exist)
- No circular imports
- Consistent import style (absolute vs relative)
- No unused imports
```

### Agent 2: Type Safety Audit
```
Run pyright on all modified Python files
Run tsc --noEmit on all modified TypeScript files
Check for:
- Any type errors
- Bare 'Any' types that should be specific
- Mismatched function signatures
- Missing return type annotations
```

### Agent 3: API Contract Audit
```
For any new/modified API endpoints:
- Verify Pydantic response models match TypeScript interfaces
- Check argument ordering is correct
- Verify async session handling is proper
- Check datetime formats are timezone-aware
```

### Agent 4: Integration Test
```
For each new endpoint:
- curl with realistic payloads
- Verify response structure matches schema
- Check error handling for bad inputs
- Verify database state after mutations
```

## Quick Command

Paste this to spawn all agents:
```
Spawn 4 parallel review agents:
1. Check all import paths are valid and modules exist
2. Run pyright on modified .py files, tsc on modified .ts/.tsx files, fix all errors
3. Verify API endpoint response types match TypeScript frontend interfaces exactly
4. curl every new/modified API endpoint and verify responses

Collect findings, deduplicate, fix every issue, then re-run tests to confirm.
```

## Output Format

Each agent reports:
```
## Agent [N]: [Name]
- Files checked: [count]
- Issues found: [count]
- Fixed: [list]
- Needs attention: [list]
```
