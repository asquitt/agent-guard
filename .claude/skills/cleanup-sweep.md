# Cleanup Sweep

Run a systematic dead code and duplication audit across the codebase.

## Checklist

### Backend (`agentguard-backend/backend/app/`)
1. **Orphaned functions**: grep for `def ` in services/utils, verify each has a caller
2. **Commented imports**: `grep -rn '^\s*#\s*from\|^\s*#\s*import' app/`
3. **Stub tasks**: check `celery_app.py` beat schedule — every task must do real work
4. **Unused schemas**: check `app/schemas/` — every class must be used in an API router
5. **Duplicated constants**: check for identical dicts/maps defined in multiple files
6. **Bare excepts**: `grep -rn 'except:' app/` (should be 0)
7. **Security**: `grep -rn 'f"SELECT\|f"INSERT\|f"UPDATE\|f"DELETE' app/` (should be 0)

### Frontend (`agentguard-frontend/src/`)
1. **Unused types**: check `types/index.ts` — every export must be imported somewhere
2. **Duplicated constants**: `grep -rn 'const SEVERITY_COLORS\|const STATUS_COLORS' src/app/` (should be 0, all in constants.ts)
3. **Unused API functions**: check `lib/api/` — every export must be called
4. **dangerouslySetInnerHTML**: `grep -rn 'dangerouslySetInnerHTML' src/` (should be 0)

### Output
Report findings as a numbered list with file:line references. Fix anything found.
