# Comprehensive Bug Sweep

Launch parallel agents to audit different subsystems and auto-fix issues.

## Usage
Run `/bug-sweep` after major implementations or when suspecting hidden bugs.

## Full Sweep Prompt

Paste this for comprehensive sweep:

```
Run a comprehensive parallel bug sweep. Spawn these agents simultaneously:

Agent 1 — API Contract Audit:
Check every API endpoint for correct argument ordering, proper async session handling, and that response types match frontend TypeScript interfaces.

Agent 2 — Database Consistency:
Verify all migrations apply cleanly, check for JSONB vs JSON column type mismatches, timezone-aware vs naive datetime issues, and enum type conflicts.

Agent 3 — Import & Type Safety:
Run pyright across the entire codebase, trace all import paths for correctness, and verify no variable shadowing or name collisions.

Agent 4 — Integration Testing:
Run the full test suite, then curl every API endpoint with realistic payloads and verify responses.

Collect all findings, deduplicate, fix every issue found, re-run the full test suite to confirm, and commit with a summary of all fixes.
```

## Common Bug Patterns to Check

1. **Import Errors**
   - Wrong module paths
   - Missing imports
   - Wrong variable names

2. **Type Mismatches**
   - API types not matching component props
   - Field names different between backend/frontend
   - Nullability inconsistencies

3. **DateTime Issues**
   - Timezone-naive vs timezone-aware
   - UTC vs local time confusion
   - Serialization format mismatches

4. **JSONB Syntax**
   - Using JSON operators instead of JSONB
   - Wrong query syntax for PostgreSQL JSONB columns

5. **Migration Conflicts**
   - Conflicting migration versions
   - Missing model imports in `__init__.py`
   - Enum type conflicts

## Quick Targeted Sweeps

### Type Check Only
```bash
cd backend && pyright app/ --level warning
cd frontend && npx tsc --noEmit
```

### Import Check Only
```bash
python -c "
import ast, glob
for f in glob.glob('app/**/*.py', recursive=True):
    try:
        ast.parse(open(f).read())
    except SyntaxError as e:
        print(f'{f}: {e}')
"
```
