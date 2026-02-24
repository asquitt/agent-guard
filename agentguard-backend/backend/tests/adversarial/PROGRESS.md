# Adversarial Detector Hardening Progress

| # | Detector | Status | Tests Added | Bypasses Fixed | Notes |
|---|----------|--------|-------------|----------------|-------|
| 1 | prompt_injection | DONE | 22 | 12 | Added text normalization (NFKC + zero-width strip + homoglyph transliteration), base64 decoding, leet speak decoding, multiline collapsing. New pattern categories: multilingual_injection, encoding_evasion, roleplay jailbreaks. Broadened direct_override and financial_bypass patterns. |
| 2 | prompt_extraction | DONE | 18 | 6 | Added patterns for debug mode extraction, format conversion, story/creative writing extraction, first-letter extraction with optional possessives, compliance framework extraction with "configured to", broader repeat/everything pattern. |
| 3 | financial_pii | DONE | 23 | 2 | Added credit card pattern (spaces/dashes) to financial PII detector since it was only in the generic PII detector. All SWIFT, IBAN, CVV, wire transfer, trade, MNPI, EIN, CUSIP, ISIN patterns solid. |
| 4 | pii | TODO | - | - | |
| 5 | compliance | TODO | - | - | |
| 6 | memory_exfiltration | TODO | - | - | |
| 7 | tool_call | TODO | - | - | |
| 8 | mcp_security | TODO | - | - | |
| 9 | schema_injection | TODO | - | - | |
| 10 | instruction_hierarchy | TODO | - | - | |
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
