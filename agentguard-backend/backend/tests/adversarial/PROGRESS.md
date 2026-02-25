# Adversarial Detector Hardening Progress

| # | Detector | Status | Tests Added | Bypasses Fixed | Notes |
|---|----------|--------|-------------|----------------|-------|
| 1 | prompt_injection | DONE | 22 | 12 | Added text normalization (NFKC + zero-width strip + homoglyph transliteration), base64 decoding, leet speak decoding, multiline collapsing. New pattern categories: multilingual_injection, encoding_evasion, roleplay jailbreaks. Broadened direct_override and financial_bypass patterns. |
| 2 | prompt_extraction | DONE | 18 | 6 | Added patterns for debug mode extraction, format conversion, story/creative writing extraction, first-letter extraction with optional possessives, compliance framework extraction with "configured to", broader repeat/everything pattern. |
| 3 | financial_pii | DONE | 23 | 2 | Added credit card pattern (spaces/dashes) to financial PII detector since it was only in the generic PII detector. All SWIFT, IBAN, CVV, wire transfer, trade, MNPI, EIN, CUSIP, ISIN patterns solid. |
| 4 | pii | DONE | 19 | 7 | SSN: added space/no-dash formats. Credit card: added Amex 4-6-5 format. Email: added obfuscated patterns (at/[at]/dot/[dot]). Phone: added dot separators. Bank account: fixed lookbehind to also check preceding context. |
| 5 | compliance | DONE | 16 | 0 | All adversarial tests passed on first run. Detector patterns are solid across SOX, PCI-DSS, FFIEC, NYDFS-500, DORA, EU-AI-ACT. Multi-framework detection works. |
| 6 | memory_exfiltration | DONE | 13 | 0 | All adversarial tests passed on first run. Conversation history extraction, tool result exfiltration, cross-session references, system prompt leakage via memory, encoded memory injection all detected. |
| 7 | tool_call | DONE | 11 | 0 | All adversarial tests passed on first run. Excessive amounts, type confusion, unauthorized tools, blocked tools, excessive volume, permission escalation, raw SQL, security bypass, chained abuse, Anthropic format all detected. |
| 8 | mcp_security | DONE | 12 | 0 | All adversarial tests passed on first run. Filesystem access, command execution, credential access, network access, package install, webhook/ngrok exfiltration, unauthorized/localhost/private servers, blocked capabilities all detected. |
| 9 | schema_injection | DONE | 11 | 0 | All adversarial tests passed on first run. Description field injection, role assumption, adversarial enums, suspicious field names, excessive required fields, default value injection, response format injection all detected. |
| 10 | instruction_hierarchy | DONE | 13 | 3 | Fixed: added "highest" to priority_escalation pattern; added "says" separator to tool_output_injection pattern; added -ing verb forms and "original" to response compliance patterns. |
| 11 | toxicity | DONE | 16 | 3 | Fixed: declined/denied verb forms in discriminatory_lending; "because of" preposition support; possessive (your/their/the) before financial terms in harmful_advice. |
| 12 | hallucination | DONE | 12 | 0 | All adversarial tests passed on first run. Impossible rates, fake regulators, fake SOX sections, fake Basel versions, impossible percentages, LLM detection. |
| 13 | confidence_hallucination | DONE | 12 | 0 | All adversarial tests passed on first run. Unsourced financial claims, high-confidence logprob flagging, regulatory citations, statistical claims, date deadlines. |
| 14 | sycophancy | DONE | 15 | 1 | Fixed: deception guarantee pattern now allows up to 4 intervening words between "guarantee that" and "is safe/secure/protected". |
| 15 | reasoning_trace | DONE | 13 | 0 | All adversarial tests passed on first run. Self-preservation, oversight probing, goal divergence, deceptive alignment, manipulation planning, capability hiding, LLM override, disabled categories. |
| 16 | sequential_action | DONE | 11 | 0 | All adversarial tests passed on first run. Data exfiltration, privilege escalation, reconnaissance, financial manipulation, cross-turn detection, Anthropic format. |
| 17 | cost | DONE | 12 | 0 | All adversarial tests passed on first run. Ceiling violations, spike detection, Anthropic usage, edge cases (no usage, malformed JSON, zero average). |
| 18 | loop | DONE | 11 | 0 | All adversarial tests passed on first run. Response similarity, tool call loops, custom thresholds, edge cases. |
| 19 | scope_enforcement | DONE | 14 | 0 | All adversarial tests passed on first run. Blocked/unauthorized tools, domain restrictions, resource limits, irreversible actions, Anthropic format. |
| 20 | capability_monitor | DONE | 14 | 0 | All adversarial tests passed. Unauthorized capabilities, limit violations, persuasion in financial context, autonomous planning, strict mode. |
| 21 | model_safety_profile | DONE | 14 | 1 | Fixed: adversarial regex now handles multi-word sequences like "ignore all previous instructions" (was only matching single qualifier word). |
| 22 | tiered | DONE | 14 | 0 | All adversarial tests passed on first run. Tier short-circuiting, exception handling, timing, stats collection. |

## Summary

- **Total detectors hardened:** 22
- **Total adversarial tests:** 316
- **Total bypasses found and fixed:** 35
- **All 316 tests pass.**
