# AgentGuard Tech Debt Tracker

**Last Updated:** 2026-02-14

## File Size Warnings (>500 lines)

| File | Lines | Action |
|------|-------|--------|
| `tests/functional_test.py` | 899 | Split into per-feature test files |
| `services/interpretability_service.py` | 692 | Approaching limit — extract constants/utils |
| `services/sandbox/sandbox_service.py` | 579 | Monitor — already in package |
| `api/proxy.py` | 566 | Monitor — may split streaming logic |
| `api/governance.py` | 515 | Monitor |
| `frontend/src/types/index.ts` | 506 | Split into per-feature type files |
| `agents/[agentId]/policies/page.tsx` | 486 | Extract form and list sub-components |
| `agents/page.tsx` | 421 | Extract table and filter sub-components |

## Known Issues

### Backend
- **Billing router** (83 lines): Minimal Stripe integration — needs plan management, usage dashboards, invoice history
- **Detector router** (169 lines): CRUD only — no tuning UI, no A/B testing, no auto-threshold adjustment
- **Team management**: Not implemented — only admin/member roles, no granular RBAC

### Frontend
- **Settings → Team Management**: Placeholder "Coming soon" text
- **Billing page**: Incomplete — lacks plan comparison and usage breakdown
- **Dashboard**: Static cards only — no custom dashboard builder

### SDK
- **No LangGraph integration**: Only LangChain and LlamaIndex callbacks
- **No CrewAI integration**: Popular framework missing
- **No Terraform provider**: Infrastructure-as-code support missing

## Type Safety

- No `Any` overuse detected in current codebase
- No bare `except:` clauses found
- All models properly typed with SQLAlchemy Column types

## Resolved

| Date | Item | Resolution |
|------|------|-----------|
| 2026-02-14 | SDK returns `unknown` types | Added typed responses to both Python and Node SDKs |
| 2026-02-14 | No retry logic in SDKs | Added exponential backoff with 429/5xx handling |
| 2026-02-14 | No framework integrations | Added LangChain, LlamaIndex, OTel integrations |
| 2026-02-14 | No custom SDK exceptions | Added error hierarchy matching HTTP status codes |
