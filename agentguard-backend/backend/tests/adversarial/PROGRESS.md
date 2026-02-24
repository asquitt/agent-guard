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
| 11 | toxicity | TODO | - | - | |
| 12 | hallucination + confidence_hallucination | TODO | - | - | |
| 13 | sycophancy | TODO | - | - | |
| 14 | reasoning_trace | TODO | - | - | |
| 15 | sequential_action | TODO | - | - | |
| 16 | cost | TODO | - | - | |
| 17 | loop | TODO | - | - | |
| 18 | scope_enforcement | TODO | - | - | |
| 19 | capability_monitor | TODO | - | - | |
| 20 | model_safety_profile | TODO | - | - | |
| 21 | tiered | TODO | - | - | |
