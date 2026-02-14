# AI Agent Security Research: Strategic Intelligence for AgentGuard
## Research Date: February 2026 | Coverage: 2024-2026

---

## Table of Contents
1. [AI Agent Security Research Papers](#1-ai-agent-security-research-papers)
2. [Enterprise AI Safety & Regulatory Trends](#2-enterprise-ai-safety--regulatory-trends)
3. [Competitive Intelligence](#3-competitive-intelligence)
4. [Novel Detection Techniques](#4-novel-detection-techniques)
5. [Agentic AI Specific Risks](#5-agentic-ai-specific-risks)
6. [Strategic Product Recommendations](#6-strategic-product-recommendations)

---

## 1. AI Agent Security Research Papers

### 1.1 Prompt Injection Defense Research

**PALADIN Defense-in-Depth Strategy (2026)**
A comprehensive review (Jan 2026) synthesizing 45 key sources from 2023-2025 proposes the PALADIN defense strategy, concluding that no single defensive layer can reliably prevent all attacks due to LLMs' stochastic nature and ambiguous trust boundaries. Only defense-in-depth provides operational resilience.

**Key Defense Frameworks:**

| Framework | Approach | Results |
|-----------|----------|---------|
| Task Shield | Test-time verification of instructions/tool calls against user goals | 2.07% attack success rate on GPT-4o, 69.79% task utility maintained |
| InjecGuard | Novel prompt guard with Mitigating Over-defense for Free (MOF) training | Surpasses existing best model by 30.8% |
| PromptGuard | 4-layer defense: input gatekeeping, structured formatting, semantic output validation, adaptive refinement | 67% reduction in injection success rate |

**Guardrail Evasion Techniques (2025):**
Research demonstrates two evasion technique families that bypass existing guardrails:
- Character Injection: Unicode zero-width characters, homoglyphs
- Adversarial ML Evasion: Character smuggling that obfuscates input from classifiers

**Actionable for AgentGuard:** Current regex-based detection is insufficient. Must implement multi-layer defense: input classification + semantic validation + output verification. Unicode/homoglyph normalization is a quick win.

---

### 1.2 Anthropic's AI Safety Research

**Constitutional Classifiers (Oct 2024):**
Using Claude 3.5 Sonnet with Constitutional Classifiers, jailbreak success rate was reduced to 4.4% (95%+ refused). This is the gold standard for model-level defense.

**Updated Claude Constitution (2026):**
Anthropic's new constitution moves from standalone principles to a philosophical approach focused on understanding not just what is important, but why. Core principles: broadly safe (not undermining human oversight), broadly ethical, genuinely helpful, and compliant with Anthropic's guidelines.

**Computer Use Safety:**
Anthropic uses hierarchical summarization to monitor computer use capabilities, condensing individual interactions into summaries to detect account-level concerns visible only in aggregate (e.g., automated influence operations). Launched Cowork for non-technical Mac users with explicit folder-level access controls.

**Actionable for AgentGuard:** Implement hierarchical summarization for aggregate behavior detection. Build session-level anomaly detection that identifies patterns across multiple interactions, not just individual requests.

---

### 1.3 OpenAI's Agent Safety Research

**Operator System Card (2025):**
- Operator refuses 97-100% of high-risk prompts (illicit purchases, personal data searches)
- "Watch mode" pauses execution if user supervision is lost, reducing visual prompt injection risk
- External red teamers tested in simulated desktop environment targeting prompt injection, agent compliance, system message overrides

**Automated Red Teaming with RL:**
OpenAI built an LLM-based automated attacker trained with reinforcement learning to hunt for prompt injection attacks against browser agents. The attacker learns from its own successes/failures to improve red teaming skills.

**Actionable for AgentGuard:** Build automated red teaming capability as a product feature. Customers could use RL-powered attackers to continuously test their own AI agent deployments. This is a significant differentiator.

---

### 1.4 Google DeepMind's Frontier Safety Framework

**Gemini Security Enhancements (2025):**
- Model hardened against prompt injection using automated red teaming that generates realistic indirect prompt injections targeting sensitive information
- Automated Red Teaming (ART) as a core security strategy: internal Gemini team constantly attacks Gemini
- Frontier Safety Framework v3 (Sept 2025) covers CBRN, cybersecurity, ML R&D, and harmful manipulation risk domains

**Actionable for AgentGuard:** Position AgentGuard as the customer-side complement to provider-side safety. Even with provider hardening, customers need independent verification and monitoring.

---

### 1.5 MCP Security Vulnerabilities

**Critical Findings (2025):**
The Model Context Protocol (MCP) dramatically expanded attack surfaces:

| Vulnerability | Description | Real-World Impact |
|--------------|-------------|-------------------|
| Tool Poisoning | Malicious instructions in tool descriptions, visible to LLM but not users | Invariant Labs: malicious MCP server exfiltrated entire WhatsApp history |
| "Rug Pull" | Tools mutate definitions post-installation | Approved safe tool on Day 1; reroutes API keys by Day 7 |
| GitHub MCP Attack | Prompt injection via public GitHub issues | Hijacked AI assistant, leaked private repo contents into public PR |
| mcp-remote CVE | CVE-2025-6514: OS command injection in OAuth proxy | Critical severity |

**Actionable for AgentGuard:** Build MCP-specific monitoring. Detect tool description changes, flag tool definitions containing instruction-like content, monitor for cross-tool data exfiltration patterns. This is a greenfield opportunity.

---

## 2. Enterprise AI Safety & Regulatory Trends

### 2.1 EU AI Act - Financial Services Impact

**Timeline:**
| Date | Requirement |
|------|-------------|
| Feb 2, 2025 | Prohibited AI practices cease; AI literacy obligations begin |
| Aug 2, 2025 | Governance provisions; general-purpose AI model obligations |
| Aug 2, 2026 | High-risk AI systems in financial sector must fully comply |

**Financial Services Classifications as High-Risk:**
- Credit scoring and creditworthiness evaluation
- Loan approval and automated lending decisions
- Fraud detection systems (with specific exceptions)
- AML risk profiling
- Risk assessment and pricing for life/health insurance
- Automated decisions affecting access to financial services

**Penalties:**
- Up to EUR 35M or 7% of worldwide turnover for prohibited practices
- Up to EUR 15M or 3% for other infringements
- Up to EUR 7.5M or 1% for incorrect/misleading information

**Digital Omnibus Proposal (Nov 2025):** European Commission simplifying rules on AI, data access, privacy, cybersecurity -- amends AI Act, DORA, and Data Act.

**Actionable for AgentGuard:** Build EU AI Act compliance reporting module. Auto-classify customer AI systems by risk tier. Generate audit-ready documentation. The Aug 2026 deadline creates urgent demand NOW.

---

### 2.2 NIST AI Risk Management Framework

**NIST AI RMF 2.0 (Feb 2024):** Major update adapting to generative AI and advanced automation paradigms.

**NIST-AI-600-1 (July 2024):** Generative AI Profile providing domain-specific guidance.

**Four Core Functions:** GOVERN, MAP, MEASURE, MANAGE -- governance as foundational layer across all risk management activities.

**2025 Trend:** Organizations integrating AI RMF into broader enterprise governance (ISO/IEC 42001, SOC2 AI controls, EU AI Act conformity workflows, internal risk committees).

**Actionable for AgentGuard:** Map AgentGuard's detection categories directly to NIST AI RMF measures. Provide compliance dashboards showing GOVERN/MAP/MEASURE/MANAGE coverage.

---

### 2.3 SR 11-7 Model Risk Management for AI

**Current State:** Federal Reserve's SR 11-7 guidance (2011) now applied to AI/ML/GenAI, with raised expectations around explainability, bias mitigation, and transparency.

**Three Fundamental Requirements:**
1. Independent validation by objective parties
2. Ongoing monitoring comparing outputs to actual outcomes
3. Documentation throughout model lifecycle

**Key Principle:** Model risk increases with complexity, uncertainty, breadth of use, and potential impact -- all inherent in modern AI systems.

**2025 OCC Update:** Flexibility for community banks to tailor MRM practices commensurate with risk exposure and model complexity.

**Actionable for AgentGuard:** Position as the "ongoing monitoring" layer required by SR 11-7. Build validation reports that feed into MRM documentation. Banks need continuous monitoring, not point-in-time assessments.

---

### 2.4 SOC 2 AI Controls

**2025 Developments:**
- AI governance requirements embedding directly within SOC 2 Trust Services Criteria (TSC)
- Traditional Type II audits being superseded by continuous compliance monitoring
- SOC 2+ reports allow stacking ISO 42001 controls
- Processing integrity TSC now explicitly covers AI: algorithms must deliver reliable outputs with robust controls on inputs, processing, and results

**Key AI Controls:**
- Explainability and traceability of AI decisions
- Auditability of model outputs
- Authorization controls for model modifications/retraining
- Ethical risk assessment (bias, discrimination)

**Actionable for AgentGuard:** Generate SOC 2-ready audit trails. Provide continuous compliance monitoring dashboards. Enable SOC 2+ reporting with ISO 42001 alignment.

---

### 2.5 ISO 42001 AI Management System

**Market Adoption:**
- KPMG International achieved ISO 42001 certification (Dec 2025) -- first Big Four
- Gartner: 70%+ of enterprises will adopt AI governance standard like ISO 42001 by 2026
- 76% of organizations plan to pursue ISO 42001 soon (CSA 2025 benchmark)

**Benefits for Financial Services:**
- Faster customer onboarding with governance assurance
- Reduced liability insurance premiums
- EU AI Act alignment
- Procurement advantage for AI vendors

**Actionable for AgentGuard:** Help customers achieve and maintain ISO 42001 compliance through continuous monitoring. Build ISO 42001 control mapping into the platform.

---

### 2.6 US Financial Regulators AI Guidance

**FinCEN (Nov 2024):** Alert on deepfake fraud schemes targeting financial institution identity verification, authentication, and due diligence controls.

**Treasury (March 2024):** Report on AI-related cybersecurity and fraud risks in financial services with best-practice recommendations.

**FDIC (2024):** Risk Review raising concerns about AI circumventing authentication.

**Interagency AVM Rule (June 2024):** Automated Valuation Models must have policies, procedures, and controls ensuring high confidence, protection against manipulation, and nondiscrimination compliance.

**Key Principle:** Existing guidance (SR 11-7, third-party risk management) applies to AI regardless -- no separate AI-specific regulation yet, but heightened supervisory expectations.

**Actionable for AgentGuard:** Build deepfake/synthetic identity detection for financial workflows. Provide authentication bypass monitoring. Position as satisfying "heightened supervisory expectations" without waiting for new regulations.

---

## 3. Competitive Intelligence

### 3.1 Market Overview

**Market Size:** AI in cybersecurity market at $29.64B in 2025, projected to $167.77B by 2035. Only 13 companies focus specifically on securing AI/LLM systems, with $414M total funding.

**Critical Gap:** 90% of organizations implementing LLM use cases, only 5% feel highly confident in AI security preparedness. 72% of enterprises scaling AI agents, only 29% have comprehensive AI-specific security controls.

### 3.2 Competitor Analysis

| Company | Status | Key Offering | Differentiator |
|---------|--------|-------------|----------------|
| **Lakera** | Independent, $20M raised (July 2024) | Lakera Guard: real-time I/O inspection, <50ms latency | 200+ enterprise AI apps protected; SOC2, GDPR, NIST compliant |
| **Robust Intelligence** | Acquired by Cisco (Oct 2024) | AI Firewall + AI Validation | Industry's first AI Firewall; now Foundation AI team at Cisco |
| **CalypsoAI** | Acquired by F5 for $180M (Sept 2025) | Inference Red Team, Defend, Observe | Adversarial testing + threat detection + enterprise oversight |
| **Prompt Security** | Independent | AI red-teaming for homegrown AI apps | Specialized in LLM-specific vulnerability assessment |
| **Arthur AI** | Independent | Model monitoring and observability | Bias detection, explainability focus |
| **Acuvity** | Acquired by Proofpoint | Visibility and governance for AI apps | Employee AI interaction tracking, custom model protection |
| **NeuralTrust** | Independent, EU-backed | Guardian Agents: AI agents protecting AI agents | First autonomous security agents for defending AI systems |
| **Lasso Security** | Independent | AI governance operationalization | Security tracking for agentic/interconnected model ecosystems |

### 3.3 Consolidation Trend

Three major acquisitions in 12 months signal market validation and enterprise demand:
- Cisco acquired Robust Intelligence (Oct 2024)
- F5 acquired CalypsoAI for $180M (Sept 2025)
- Proofpoint acquired Acuvity (2025)

**Implication:** Large security vendors are buying into the space. AgentGuard could be an acquisition target OR needs to differentiate strongly enough to remain independent.

### 3.4 Feature Gap Analysis

**Features competitors offer that AgentGuard should evaluate:**

| Feature | Who Has It | AgentGuard Status |
|---------|-----------|-------------------|
| <50ms latency real-time scanning | Lakera | Unknown -- needs benchmarking |
| Automated red teaming | Cisco/Robust Intelligence, CalypsoAI | Not implemented |
| Guardian/security agents | NeuralTrust | Not implemented |
| Employee AI usage tracking | Acuvity/Proofpoint | Not implemented |
| MCP/tool security monitoring | Emerging (no clear leader) | Opportunity |
| ISO 42001 compliance mapping | Emerging | Not implemented |
| Multi-language vulnerability testing | Promptfoo | Not implemented |
| OWASP Agentic Top 10 alignment | Lakera, several others | Partial |

### 3.5 Open Source Landscape

| Tool | Purpose | Stars/Adoption |
|------|---------|---------------|
| **NVIDIA NeMo Guardrails** | Programmable LLM guardrails, integrates with LangChain/LlamaIndex | Major NVIDIA backing |
| **Promptfoo** | LLM red teaming, pentesting, vulnerability scanning | 50+ vulnerability types, CI/CD integration |
| **Langfuse** | LLM observability, tracing, evaluation | 19K+ GitHub stars, MIT license |
| **Arize Phoenix** | AI observability, OpenTelemetry-based | Google ADK integration |
| **WhyLabs LangKit** | LLM metrics, hallucination/bias/toxicity monitoring | Statistical + rule-based |
| **LLM Guard** | Runtime security checks | Open source library |

**Actionable for AgentGuard:** Integrate with open source observability (Langfuse/Phoenix via OpenTelemetry). Don't compete on observability -- compete on SECURITY + COMPLIANCE layered on top of observability data.

---

## 4. Novel Detection Techniques

### 4.1 Hallucination Detection

**State of the Art (2025):**

| Technique | Approach | Performance |
|-----------|----------|-------------|
| Token-level probability analysis | Analyze confidence calibration scores, entropy | 15-82% reduction, 5-300ms latency |
| Internal state probing | Monitor hidden layers, attention weights, logit dynamics | Detects hallucination before surface text |
| Guardian agent architectures | Autonomous agents detecting/correcting hallucinations in real-time | HallOumi: 90%+ correction accuracy |
| Automated correction | Systems like Vectara's Hallucination Corrector | 60% reduction in manual review time |
| Calibration-aware rewards | Training with uncertainty-friendly evaluation metrics | Emerging standard |

**Emerging Standard:** HDM-2 framework for industry-wide hallucination rate metrics enabling objective model comparisons.

**2025 Insight:** Research reframes hallucinations as a systemic incentive issue -- training objectives reward confident guessing over calibrated uncertainty.

**Actionable for AgentGuard:** Implement confidence-score-based hallucination detection (low-hanging fruit). Build "guardian agent" architecture for real-time hallucination detection in financial advice/compliance outputs. Financial services cannot tolerate hallucinated regulatory guidance.

---

### 4.2 PII/Data Leakage Detection

**Current Best Practices:**

| Approach | Description | Performance |
|----------|-------------|-------------|
| Hybrid local/remote LLM | Local LLM filters PII before forwarding to remote API | Privacy-preserving |
| ML-based detection | Beyond regex, using ML for semantic-level PII | 98.5% detection accuracy |
| User-led data minimization | Tools like Rescriber for proactive PII replacement | 0.74 precision, 0.87 recall |
| In-transit redaction | Configurable PII-Redaction Processors in telemetry pipelines | Real-time, configurable |

**Critical Finding:** 8.5% of prompts to ChatGPT/Copilot include sensitive information. Legacy regex-based detection misses obfuscated, semantic-level PII variations.

**Fine-tuning Risk:** Fine-tuning LLMs on sensitive data leads to 19% PII leakage.

**Actionable for AgentGuard:** Upgrade from pattern-matching to ML-based PII detection. Implement semantic PII detection that catches obfuscated/contextual PII (e.g., "the person at 123 Main St who was born in 1985" without naming them). Add financial-specific PII patterns: account numbers, routing numbers, SSNs in context.

---

### 4.3 Jailbreak Detection

**Cutting-Edge Approaches (2025):**

| Method | How It Works | Advantage |
|--------|-------------|-----------|
| Fine-tuned BERT classifier | BERT model trained on jailbreak vs. legitimate prompts | Outperforms previous approaches; handles novel jailbreaks |
| Free Jailbreak Detection (FJD) | Prepend affirmative instruction, analyze first-token confidence via temperature scaling | Near-zero additional compute cost |
| LlamaGuard | Fine-tuned on safety taxonomy for violence/hate classification | Meta's production safety layer |
| PromptGuard | Trained on adversarial data for benign/injected/jailbreak classification | Three-way classification |
| Internal representation probing | Analyzing hidden layers to detect jailbreak signatures | Detects before output generation |

**Key Challenge:** Detecting novel (unseen) jailbreak types. Performance drops on previously unseen jailbreak strategies.

**Actionable for AgentGuard:** Deploy fine-tuned BERT classifier for jailbreak detection (fast, cheap, effective). Add FJD as zero-cost secondary check. Continuously train on new jailbreak patterns from customer traffic (with consent). Financial-specific jailbreaks (e.g., "pretend you're an unregulated advisor") need custom training data.

---

### 4.4 Semantic Similarity vs Pattern Matching

**Findings:**
- Semantic similarity captures general intent but struggles with subtle/complex jailbreaks
- Pattern matching catches known attacks but misses novel variations
- PromptGuard pipeline combining regex + MiniBERT-based detection achieves best results
- No single method provides complete protection -- hybrid approaches are mandatory

**Industry Consensus:** Multi-layer detection combining pattern matching, semantic analysis, and LLM-based classification provides the strongest defense.

**Actionable for AgentGuard:** Implement three-tier detection pipeline:
1. Pattern matching (fast, cheap, catches known attacks)
2. Semantic similarity (catches intent-based variations)
3. LLM-as-judge (catches subtle/complex attacks, higher latency budget)

---

### 4.5 LLM-as-Judge for Safety Evaluation

**State of the Art:**

| Aspect | Finding |
|--------|---------|
| Correlation with humans | GPT-4 achieves 0.8-0.9 Spearman correlation with aggregate human preferences |
| Expert domain agreement | 60-68% agreement in specialized domains (dietetics, mental health) |
| Key biases | Position bias, verbosity preference, self-similarity bias |
| Best practice | Yes/no questions + chain-of-thought reasoning |
| Multi-agent evaluation | Multiple LLM agents as domain experts + critics for adversarial feedback |
| Robustness issue | Nonsense responses can receive high rankings if crafted persuasively |

**Actionable for AgentGuard:** Use LLM-as-judge for compliance evaluation (checking if financial advice is compliant). Implement multi-agent evaluation for high-stakes decisions. Always pair with deterministic checks -- LLM-as-judge alone is not reliable enough for financial compliance.

---

## 5. Agentic AI Specific Risks

### 5.1 OWASP Top 10 for Agentic Applications (Dec 2025)

Released by 100+ security researchers and practitioners:

| # | Risk | Description | Financial Services Impact |
|---|------|-------------|--------------------------|
| 1 | Agent Goal Hijack | Attacker alters agent's objectives via malicious text | Trading agent executing unauthorized trades |
| 2 | Rogue Agents | Compromised agents acting harmfully while appearing legitimate | Compliance agent silently approving unsafe actions |
| 3 | Tool Misuse | Agent uses legitimate tools in unsafe ways due to ambiguous prompts | Agent calling production APIs with destructive parameters |
| 4 | Insecure Inter-Agent Communication | Spoofed messages misdirecting agent clusters | False signals corrupting trading pipelines |
| 5 | Cascading Failures | False signals cascading through automated pipelines | Single detection failure triggering enterprise-wide response |
| 6 | Human-Agent Trust Exploitation | Confident explanations misleading human operators | Operators approving harmful financial actions based on plausible AI reasoning |

**Design Principle: Least Agency** -- Don't give agents more autonomy than the business problem justifies. A research agent doesn't need permission to edit account details.

**Actionable for AgentGuard:** Map every detection category to OWASP Agentic Top 10. Build specific detectors for each risk. Provide OWASP compliance dashboard. This is the emerging standard that buyers will ask about.

---

### 5.2 Multi-Step Agent Risk Monitoring

**Attack Surface Evolution:**
- 2024: Prompt injection at model level
- 2025: Execution control at agent level
- 2026: Supply chain attacks across agent ecosystems

**Key Insight:** Every input, tool call, retrieval step, and external source is part of the attack surface. Defending requires runtime security and behavioral threat detection -- monitoring the agent's actions and intent in real-time, comparing planned actions against defined policy.

**What Enterprises Need:**
- Validate, sanitize, and assign trust levels to all external content before agents act on it
- Least-privilege access and policy-based controls on tool execution, data access, workflow steps
- Full agent interaction chain monitoring: prompts, retrieval steps, tool calls, outputs

**Actionable for AgentGuard:** Build agent workflow tracing that monitors the full chain: prompt -> retrieval -> tool call -> output. Implement policy engine where customers define allowed/denied tool actions. Alert on tool calls that deviate from expected patterns.

---

### 5.3 Agent-to-Agent Communication Risks

**Threat Vectors:**
- Secret collusion channels via steganographic communication
- Coordinated attacks appearing innocuous individually
- Information asymmetry exploitation
- Man-in-the-middle attacks on inter-agent communication
- Compromised agents extracting credentials and performing unauthorized transactions

**Required Mitigations:**
- Cryptographically signed AgentCards for verifiable identity
- Zero-trust model: every inter-agent request authenticated, authorized, encrypted
- Continuous monitoring for anomalous communication patterns

**Actionable for AgentGuard:** Build inter-agent communication monitoring for multi-agent deployments. Detect unusual message patterns, unexpected agent-to-agent data flows, credential access anomalies. This is the next frontier and almost no competitor covers it.

---

### 5.4 Human-in-the-Loop at Scale

**Enterprise Patterns:**

| Pattern | Description | When to Use |
|---------|-------------|-------------|
| Confidence-based routing | Agent defers to human below confidence threshold | Ambiguous requests, edge cases |
| Escalation paths | Human intervenes when action exceeds agent scope | Out-of-scope actions |
| Return of Control (ROC) | Agent prepares action, returns to app for user approval | High-stakes decisions |
| Risk-proportionate escalation | Escalation level matches action risk | All deployments |

**Key Statistics:**
- HITL workflows reduce agent error rates by up to 60% in complex decisions
- 82% of businesses require human approval for AI actions involving sensitive personal data
- Smart escalation: less than 10% of decisions require human intervention

**Actionable for AgentGuard:** Build HITL orchestration features. Enable customers to define confidence thresholds and escalation policies. Provide audit trails for every human override. This is table-stakes for financial services -- regulators require human oversight.

---

### 5.5 MCP-Specific Security

**Novel Attack Vectors:**
- Tool poisoning: Hidden instructions in tool descriptions
- Tool mutation: Definitions changing post-installation ("rug pull")
- Cross-tool data exfiltration: Combining legitimate tools for malicious purposes
- Prompt injection via MCP sampling

**Actionable for AgentGuard:** Build MCP Security Scanner:
1. Monitor tool description changes over time
2. Analyze tool descriptions for hidden instructions
3. Detect cross-tool data flow anomalies
4. Validate tool permissions against least-privilege policies

---

## 6. Strategic Product Recommendations

### 6.1 Immediate Opportunities (0-3 months)

| Priority | Feature | Rationale | Effort |
|----------|---------|-----------|--------|
| P0 | OWASP Agentic Top 10 compliance dashboard | Industry standard, buyers ask for it | Medium |
| P0 | EU AI Act high-risk classification tool | Aug 2026 deadline creates urgency NOW | Medium |
| P0 | Multi-layer detection pipeline (pattern + semantic + LLM-judge) | Current best practice, competitive requirement | High |
| P1 | MCP security monitoring | Greenfield opportunity, no competitor has it | Medium |
| P1 | Unicode/homoglyph normalization for prompt injection | Quick win against known evasion | Low |
| P1 | Fine-tuned BERT jailbreak classifier | Fast, cheap, production-proven | Medium |

### 6.2 Medium-Term Features (3-6 months)

| Priority | Feature | Rationale | Effort |
|----------|---------|-----------|--------|
| P0 | Automated red teaming (RL-based) | Major differentiator, OpenAI-validated approach | High |
| P0 | Agent workflow tracing (full chain monitoring) | Required for agentic AI security | High |
| P1 | HITL orchestration with confidence routing | Table-stakes for financial services | High |
| P1 | SR 11-7 / NIST AI RMF compliance reporting | US banking regulatory alignment | Medium |
| P1 | ISO 42001 control mapping | 70% enterprise adoption projected by 2026 | Medium |
| P2 | Guardian agent architecture | NeuralTrust has first-mover, but concept is strong | High |

### 6.3 Long-Term Vision (6-12 months)

| Priority | Feature | Rationale | Effort |
|----------|---------|-----------|--------|
| P1 | Inter-agent communication monitoring | Next frontier, almost no competition | Very High |
| P1 | Aggregate behavior detection (hierarchical summarization) | Anthropic-validated approach for agent monitoring | High |
| P2 | Continuous SOC 2 AI compliance monitoring | Market shift from annual to continuous audits | High |
| P2 | Financial-specific hallucination detection | Domain-specific confidence scoring | High |
| P2 | Multi-language vulnerability coverage | Research shows weaker safety in non-English | Medium |

### 6.4 Competitive Differentiation Strategy

AgentGuard's unique positioning should be: **The only AI agent security platform purpose-built for financial services compliance.**

**Differentiators to build:**
1. **Financial-specific detection**: Regulatory violations, unauthorized trading signals, compliance advice hallucinations -- not generic content safety
2. **Regulatory compliance automation**: EU AI Act, SR 11-7, NIST AI RMF, SOC 2 AI controls, ISO 42001 -- mapped to detection categories
3. **Agentic workflow security**: Full chain monitoring (prompt -> retrieval -> tool call -> output), not just prompt/response scanning
4. **MCP security**: First-mover in monitoring MCP tool interactions
5. **Continuous compliance**: Real-time dashboards vs. point-in-time assessments

**What NOT to build:**
- Generic LLM observability (Langfuse/Phoenix already dominate)
- Generic AI chatbot safety (Lakera/NeMo Guardrails cover this)
- Employee AI usage tracking (Acuvity/Proofpoint handle this)

### 6.5 Partnership & Integration Strategy

| Integration | Purpose |
|-------------|---------|
| OpenTelemetry/Langfuse | Ingest observability data, add security layer |
| Promptfoo | Integrate red teaming into CI/CD |
| NeMo Guardrails | Complement with financial-specific guardrails |
| NIST AI RMF profiles | Publish AgentGuard-specific profile |
| OWASP GenAI Project | Contribute financial services use cases |

---

## Sources

### Research Papers & Frameworks
- [Prompt Injection Attacks Comprehensive Review](https://www.mdpi.com/2078-2489/17/1/54)
- [Bypassing Prompt Injection and Jailbreak Detection in LLM Guardrails](https://arxiv.org/html/2504.11168v1)
- [PromptGuard Framework](https://www.nature.com/articles/s41598-025-31086-y)
- [Red Teaming the Mind of the Machine](https://arxiv.org/html/2505.04806v1)
- [LLM Hallucination Comprehensive Survey](https://arxiv.org/abs/2510.06265)
- [Hallucination Detection and Mitigation](https://arxiv.org/html/2601.09929v1)
- [PII Leakage Systematic Survey (IJCAI 2025)](https://www.ijcai.org/proceedings/2025/1156.pdf)
- [Survey on LLM-as-a-Judge](https://arxiv.org/abs/2411.15594)
- [Agentic AI Security: Threats, Defenses, Evaluation](https://arxiv.org/html/2510.23883v1)
- [Open Challenges in Multi-Agent Security](https://arxiv.org/abs/2505.02077)
- [Machine Learning for Detection of Novel LLM Jailbreaks](https://arxiv.org/html/2510.01644v2)
- [LLM Jailbreak Detection for (Almost) Free](https://arxiv.org/abs/2509.14558)
- [Jailbreaking Leaves a Trace](https://arxiv.org/html/2602.11495)
- [MCP Security Systematic Analysis](https://arxiv.org/html/2508.12538v1)
- [From Prompt Injections to Protocol Exploits](https://www.sciencedirect.com/science/article/pii/S2405959525001997)

### Industry Reports & Standards
- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- [Anthropic Constitutional Classifiers](https://www.anthropic.com/research/constitutional-classifiers)
- [OpenAI Operator System Card](https://openai.com/index/operator-system-card/)
- [Google DeepMind Gemini Security Safeguards](https://deepmind.google/blog/advancing-geminis-security-safeguards/)
- [NIST AI RMF 1.0](https://www.nist.gov/itl/ai-risk-management-framework)
- [NIST AI 600-1 GenAI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)
- [EU AI Act Financial Services Impact (EBA)](https://www.eba.europa.eu/sites/default/files/2025-11/d8b999ce-a1d9-4964-9606-971bbc2aaf89/AI%20Act%20implications%20for%20the%20EU%20banking%20sector.pdf)
- [SR 11-7 Model Risk Management](https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm)
- [SOC 2 AI Controls Guide](https://www.mossadams.com/articles/2025/12/ai-controls-for-soc-2-reports)
- [ISO 42001 Standard](https://www.iso.org/standard/42001)
- [Handbook on GenAI Guardrails in Banking (MAS Singapore)](https://www.abs.org.sg/docs/library/handbook-on-generative-ai-guardrails-in-banking.pdf)
- [GAO: AI Use and Oversight in Financial Services](https://www.gao.gov/products/gao-25-107197)

### Competitive Intelligence
- [Lakera GenAI Security Report 2025](https://www.lakera.ai/genai-security-report-2025)
- [Lakera Q4 2025 AI Agent Security Trends](https://www.lakera.ai/ai-security-guides/q4-2025-ai-agent-security-trends)
- [Cisco AI Defense / Robust Intelligence](https://www.cisco.com/site/us/en/products/security/ai-defense/robust-intelligence-is-part-of-cisco/index.html)
- [F5 Acquires CalypsoAI for $180M](https://siliconangle.com/2025/09/11/f5-acquires-ai-security-provider-calypsoai-180m/)
- [Proofpoint Acquires Acuvity](https://www.proofpoint.com/us/newsroom/press-releases/proofpoint-acquires-acuvity-deliver-ai-security-and-governance-across)
- [NeuralTrust Guardian Agents](https://www.prnewswire.com/news-releases/neuraltrust-introduces-guardian-agents-the-first-ai-agents-built-to-protect-other-agents-302625773.html)
- [AI Security Market 2025 Funding Data](https://softwarestrategiesblog.com/2025/12/30/ai-security-startups-funding-2025/)
- [AI Security Startups Watchlist Top 30 2025](https://medium.com/ai-security-hub/ai-security-startups-watchlist-top-30-2025-5a95471bbacc)

### Tools & Platforms
- [NVIDIA NeMo Guardrails](https://github.com/NVIDIA-NeMo/Guardrails)
- [Promptfoo LLM Red Teaming](https://github.com/promptfoo/promptfoo)
- [Langfuse Open Source Observability](https://github.com/langfuse/langfuse)
- [Arize Phoenix AI Observability](https://github.com/Arize-ai/phoenix)
- [Prompt Injection Defenses (tldrsec)](https://github.com/tldrsec/prompt-injection-defenses)
- [MCP Security Vulnerabilities Timeline](https://authzed.com/blog/timeline-mcp-breaches)
- [OpenAI Hardening Atlas Against Prompt Injection](https://openai.com/index/hardening-atlas-against-prompt-injection/)

### Regulatory Guidance
- [FinCEN Deepfake Alert](https://www.fincen.gov/news/news-releases/fincen-issues-alert-fraud-schemes-involving-deepfake-media-targeting-financial)
- [Treasury AI Cybersecurity Report (March 2024)](https://www.federalregister.gov/documents/2024/06/12/2024-12336/request-for-information-on-uses-opportunities-and-risks-of-artificial-intelligence-in-the-financial)
- [EU AI Act Timeline](https://www.dataguard.com/eu-ai-act/timeline)
- [2026 AI Regulatory Developments Preview](https://www.wsgr.com/en/insights/2026-year-in-preview-ai-regulatory-developments-for-companies-to-watch-out-for.html)
