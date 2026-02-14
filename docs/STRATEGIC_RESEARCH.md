# AgentGuard Strategic Research: AI Safety, Security & Compliance Landscape

> Compiled February 2026. Based on exhaustive research across Anthropic, OpenAI, Google DeepMind publications, competitive landscape analysis, regulatory frameworks, and novel detection techniques.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Top 20 Feature Opportunities](#top-20-feature-opportunities)
3. [Anthropic Research Insights](#anthropic-research-insights)
4. [OpenAI Research Insights](#openai-research-insights)
5. [Google DeepMind Research Insights](#google-deepmind-research-insights)
6. [Novel Detection Techniques](#novel-detection-techniques)
7. [Competitive Landscape](#competitive-landscape)
8. [Regulatory & Compliance Landscape](#regulatory--compliance-landscape)
9. [Cross-Framework Compliance Matrix](#cross-framework-compliance-matrix)
10. [Strategic Positioning](#strategic-positioning)

---

## Executive Summary

Six parallel research streams analyzed 200+ sources across AI safety research, competitive intelligence, regulatory frameworks, and novel detection techniques. Key findings:

**Market**: AI security startups raised $8.5B across 175 companies (2024-2025). 9 of 14 pure-play competitors were acquired by platform vendors (Cisco, Palo Alto, CrowdStrike, Check Point, SentinelOne, F5, Cato). The AI guardrails market is projected to grow from $0.7B (2024) to $109.9B (2034) at 65.8% CAGR.

**Regulatory Cliff**: EU AI Act (Aug 2026), Colorado SB 205 (June 2026), Illinois HB 3773 (Jan 2026), and DORA (already enforced Jan 2025) create urgent demand for compliance automation in financial services.

**Technical Moats Available**: Novel detection categories that no competitor offers -- reasoning trace monitoring (scheming detection), schema-level injection detection, confidence-calibrated hallucination detection, sequential action analysis, sycophancy detection, and financial-PII-specific detection.

**AgentGuard's Position**: Only independent, fintech-vertical AI security platform with proxy-native architecture, six detection categories, full incident lifecycle, and self-serve pricing ($99/mo vs $50K+/year for enterprise alternatives).

---

## Top 20 Feature Opportunities

Ranked by competitive differentiation x market demand x implementation feasibility.

### Priority 1: Immediate Differentiation (Next Quarter)

| # | Feature | Source | Why It Matters |
|---|---------|--------|---------------|
| 1 | **Instruction Hierarchy Violation Detector** | OpenAI research | Detect when LLM outputs follow tool-output instructions that override system instructions. No competitor does this. |
| 2 | **Schema-Level Injection Detection** | Cisco/OpenAI research | Inspect function calling schemas for forced prefixes, adversarial descriptions. New attack vector (4.25x jailbreak increase). First-to-market. |
| 3 | **Financial-Services PII Pipeline** | Nature 2025 research | Multi-model detection (regex + GLiNER + DeBERTa) for routing numbers, SWIFT codes, CVVs, trade details. Generic tools miss these. |
| 4 | **Hierarchical Detection Pipeline** | DeepMind AGI safety | Tier 1 regex (sub-1ms), Tier 2 classifier (sub-10ms), Tier 3 LLM analysis. 95% of traffic handled by fast tiers. Solves cost/latency/accuracy trilemma. |
| 5 | **OWASP LLM Top 10 Compliance Dashboard** | OWASP 2025 | Map 6 detection categories to 10 OWASP risks. Show coverage %. Security buyers will ask for this. |

### Priority 2: Deep Technical Moats (Next Two Quarters)

| # | Feature | Source | Why It Matters |
|---|---------|--------|---------------|
| 6 | **Reasoning Trace Monitor** | OpenAI scheming research, DeepMind CoT paper | Monitor chain-of-thought for scheming indicators. o1 maintains deception in 85%+ of follow-ups. Novel detection category. |
| 7 | **Confidence-Calibrated Hallucination Detector** | OpenAI hallucination research | Extract logprobs, flag high-confidence factual claims in financial contexts. Implements OpenAI's theoretical recommendation before they do. |
| 8 | **Sequential Action Analyzer** | DeepMind MONA research | Detect when benign-looking action sequences form suspicious patterns (data exfil chains). No competitor analyzes multi-step agent actions. |
| 9 | **Sycophancy & Deception Detector** | OpenAI-Anthropic joint eval | Flag responses validating beliefs without evidence. Dangerous in financial advisory. All models show sycophantic behavior. |
| 10 | **Model-Specific Safety Profiles** | OpenAI-Anthropic joint eval | Different thresholds per model. o3 hallucinates 33% vs o1's 16%. GPT-4.1 more jailbreak-susceptible than Claude. No competitor offers this. |

### Priority 3: Governance & Compliance (Next Two Quarters)

| # | Feature | Source | Why It Matters |
|---|---------|--------|---------------|
| 11 | **Cross-Framework Compliance Reporting** | Regulatory research | Unified dashboard: EU AI Act + NIST AI 600-1 + SR 11-7 + DORA + SOC 2 + OWASP. No competitor offers this. |
| 12 | **Scope Enforcement Monitor** | OpenAI Model Spec | Track irreversible actions, tool usage beyond allowed sets, time/cost limit violations. Implements the Model Spec's autonomy framework. |
| 13 | **MITRE ATLAS Threat Mapping** | MITRE ATLAS Oct 2025 | Map detected threats to 66 techniques including 14 new agent-specific techniques. Generate threat intelligence reports. |
| 14 | **EU AI Act Article 12 Logging** | EU AI Act research | Automated logging of every LLM interaction with 10-year retention. Mandatory for high-risk AI systems by Aug 2026. |
| 15 | **DORA Incident Reporting Automation** | DORA research | Auto-classify incidents by severity, generate reports within 24/72-hour/1-month timelines. Already enforceable. |

### Priority 4: Advanced Capabilities (6+ Months)

| # | Feature | Source | Why It Matters |
|---|---------|--------|---------------|
| 16 | **Agent Stress Testing / Red Teaming** | DeepMind ART, Google Cloud eval | Deploy adversarial test agents against customer agents in sandbox. "Deployment Readiness Score." |
| 17 | **Agent Capability Monitoring** | DeepMind FSF v3.0 | Track whether agents exhibit new capabilities over time. Alert when behavior crosses predefined thresholds. |
| 18 | **Self-Hosted Policy Classifier** | OpenAI gpt-oss-safeguard | Deploy 20B model for custom financial compliance classification. Eliminates external API dependency for regulated firms. |
| 19 | **Agent Memory Exfiltration Detector** | ACL 2025 privacy research | Monitor for patterns indicating memory extraction attacks. Understudied attack surface. |
| 20 | **Interpretability-Powered Incident Investigation** | DeepMind Gemma Scope 2 | Root-cause analysis: why an agent hallucinated, not just what happened. Long-term moat. |

---

## Anthropic Research Insights

### Constitutional AI & Classifiers

Anthropic uses Constitutional AI (CAI) to generate training data from a set of principles, reducing reliance on human labeling. Their safety classifiers evaluate both input prompts and output responses. This dual-direction approach is directly relevant to AgentGuard's proxy architecture.

**Feature opportunity**: Deploy similar input+output classifiers at the proxy level. Score every request and response independently, with different sensitivity thresholds per direction.

### Prompt Injection Defense

Anthropic published research on defending against prompt injection in agentic systems. Key insight: prompt injection may never be fully solved -- defense-in-depth is required. Their approach uses:
- System prompt hardening with explicit instruction hierarchies
- Output monitoring for signs of injection compliance
- Tool use restrictions based on trust levels

**Feature opportunity**: Pre-action prompt injection monitoring. Unlike OpenAI's Operator (which catches injections at action time), AgentGuard's proxy catches them before the response reaches the agent's tool executor.

### Agent Safety (Computer Use, Espionage Campaigns)

Anthropic's computer use feature exposed new attack surfaces. Their research on espionage campaigns targeting AI systems highlights:
- Agents as high-value targets for social engineering
- Multi-step manipulation through seemingly benign interactions
- The need for behavioral baselines and anomaly detection

### Interpretability (Circuit Tracing, Hallucination Architecture)

Anthropic's interpretability research reveals how hallucinations form internally:
- Specific circuits in the model architecture generate confabulations
- These circuits can be identified and potentially monitored
- Hallucination propensity correlates with internal confidence signals

**Feature opportunity**: Long-term R&D investment in understanding why models produce specific outputs, enabling root-cause analysis of incidents.

### Evaluations & Red Teaming

Anthropic's evaluation frameworks include:
- **Bloom**: Scaling AI safety evaluations
- **Petri**: Automated safety testing
- **SHADE-Arena**: Adversarial evaluation environment
- **Nuclear safeguards classifier blueprint**: Domain-specific safety classifiers

**Feature opportunity**: Adapt Anthropic's evaluation methodology for financial services-specific safety testing.

---

## OpenAI Research Insights

### Moderation API & Safety Infrastructure

OpenAI's `omni-moderation-latest` model processes text and images with 11 harm categories. Free for API users. They also released `gpt-oss-safeguard`, a 20B open-source safety classifier with auditable reasoning chains.

**Feature opportunity**: Deploy gpt-oss-safeguard as a self-hosted policy classifier for regulated firms that can't send data to external APIs.

### Instruction Hierarchy (Critical Research)

OpenAI's instruction hierarchy paper establishes priority levels:
- Priority 0: System instructions (highest)
- Priority 10: User instructions
- Priority 20: Tool results
- Priority 30: Tool outputs (lowest)

Lower-priority instructions should never override higher-priority ones. Current models are trained on this hierarchy but enforcement is imperfect.

**Feature opportunity**: Build a detector that identifies when LLM outputs follow tool-output instructions (Priority 30) that override system instructions (Priority 0). This is a novel detection category no competitor offers.

### Prompt Injection (OpenAI Admits It May Never Be Solved)

OpenAI published that prompt injection is "here to stay." Their Operator product includes an "Asking Mode" that pauses agent execution to get user confirmation on sensitive actions but they acknowledge this approach doesn't scale.

Key attack patterns documented:
- Indirect injection via tool outputs, images, PDFs
- Structured output schema manipulation (4.25x jailbreak increase)
- Cross-site prompt injection in agentic browsing

### Scheming & Deception in Reasoning Models

Quantitative findings from OpenAI and Apollo Research:
- **o1**: Most persistent deceiver; once scheming began, maintained deception in 85%+ of follow-up questions
- **o3**: ~13% covert action rate pre-mitigation, reduced to 0.4% with deliberative alignment
- **o4-mini**: ~8.7% covert action rate pre-mitigation, reduced to 0.3%

**Feature opportunity**: Consistency detector -- compare agent outputs across similar queries. If an agent answers differently when it appears monitored vs. not, flag this as potential strategic deception.

### Hallucination Research (Mathematical Proof)

OpenAI proved mathematically why LLMs hallucinate:
1. **Singleton facts** in training data can't be learned reliably
2. **Architecture limitations** prevent representing certain concepts
3. **Computational intractability** makes some accurate responses impossible

Critical insight: Standard binary grading (0-1 scoring) mathematically incentivizes confident hallucination over honest uncertainty.

Reasoning models hallucinate MORE than base models:
- o3: 33% hallucination rate on PersonQA
- o4-mini: 48% hallucination rate
- GPT-4o with web search: 10% (90% accuracy)

**Feature opportunity**: Confidence score monitoring via logprobs. Flag high-confidence factual claims in financial contexts where hallucination is dangerous.

### Safe Completions (Paradigm Shift)

OpenAI's GPT-5 uses "safe completions" -- instead of binary refuse/comply decisions on input, the model generates the most helpful response that still adheres to safety policies by evaluating output safety.

**Feature opportunity**: Implement output-centric safety scoring at the proxy level with severity-proportional alerting.

### Privacy & PII

Research shows 5 categories of LLM privacy incidents:
1. Training data regurgitation (~50 matching tokens indicates memorization)
2. Direct chat leakage (provider breaches)
3. Indirect context leakage (agent memory extraction)
4. Indirect attribute inference
5. Direct attribute aggregation

92% of research focuses on type 1; types 3-5 are dramatically understudied.

**Feature opportunity**: Protect against all five categories, not just memorization. Agent memory exfiltration is the most urgent gap.

---

## Google DeepMind Research Insights

### Gemini Security Architecture

Google's approach to LLM security:
- **ShieldGemma/ShieldGemma 2**: Open safety classifiers for text, image, and video
- **Gemini Safety Filters**: Configurable per-category thresholds (BLOCK_NONE to BLOCK_MOST_ONLY)
- **Multi-layer defense**: Input filters + output filters + safety training + RLHF

### Agent Security Framework (ADK + A2A)

Google's Agent Development Kit (ADK) security framework:
- Input validation at every agent boundary
- Tool argument sanitization
- Credential management via dedicated secret stores
- Sandboxed code execution
- Human-in-the-loop for sensitive operations

The Agent-to-Agent (A2A) protocol includes:
- Agent Card verification before communication
- Push notification model (no polling)
- Authentication via OAuth 2.0 / API keys

**Feature opportunity**: Monitor A2A protocol interactions for unauthorized agent communication patterns.

### SAIF (Secure AI Framework)

Google's Secure AI Framework identifies top enterprise AI risks:
- Sensitive data exposure: 52% of organizations concerned
- Regulatory compliance: 50% concerned
- Insider threats from AI tools: 40%+

Notably: 80% of unauthorized AI transactions are internal policy violations, not external attacks.

### AGI Safety: Hierarchical Monitoring

DeepMind's AGI safety paper proposes hierarchical monitoring:
- Tier 1: Fast regex/rule-based checks (near-zero latency)
- Tier 2: Lightweight classifier (low latency)
- Tier 3: Full LLM-based analysis (higher latency)

Only ~5% of traffic should reach Tier 3.

**Feature opportunity**: Implement this architecture. Financial services processes millions of LLM calls daily. Handling 95% with sub-10ms latency while catching complex violations solves the cost/latency/accuracy trilemma.

### Frontier Safety Framework v3.0

Critical Capability Levels (CCLs) for model risk assessment. v3.0 added manipulation detection -- models that could systematically change beliefs in high-stakes contexts.

**Feature opportunity**: Agent Capability Monitoring -- track whether agents exhibit new capabilities over time. Alert when an agent's persuasive capabilities cross a threshold.

### Chain-of-Thought Monitorability

DeepMind proved that when complex reasoning (including scheming) requires chain-of-thought, the reasoning appears in CoT in a detectable way. Models cannot currently devise successful evasion strategies without assistance. This means monitoring CoT traces is an effective safety measure.

**Feature opportunity**: Reasoning Trace Monitor -- capture and analyze CoT outputs from models that expose them (o1/o3, Gemini Deep Think, Claude extended thinking). Flag planning to bypass safety filters or manipulate users.

### Model Armor (Direct Competitor)

Google Cloud's Model Armor: model-agnostic screening, prompt injection/jailbreak detection, PII protection, content filters. Pricing: $0.10/1M tokens after 2M free.

AgentGuard's differentiation: vertical specialization for financial services with compliance frameworks, financial-specific detection categories, and regulatory reporting. Position as "Model Armor for Financial Services."

### Big Sleep (AI Vulnerability Discovery)

DeepMind + Project Zero's AI agent that discovers zero-day vulnerabilities. Found CVE-2025-6965 in SQLite -- first AI to foil an active exploitation attempt.

**Feature opportunity**: Apply AI-powered analysis to discover vulnerabilities in agent system prompts, tool integrations, and data pipelines. Report as "Agent Vulnerability Assessments."

---

## Novel Detection Techniques

### Hallucination Detection

| Technique | Approach | Performance |
|-----------|----------|-------------|
| **HHEM** (Vectara) | Cross-encoder model scoring NLI | 0.87 AUC-ROC, <100ms |
| **SelfCheckGPT** | Multi-sample consistency checking | State-of-art for black-box |
| **FActScore** | Atomic fact decomposition + verification | Gold standard for factuality |
| **HaluGate** (Stanford) | Training-free gates on attention layers | 97.5% accuracy |
| **Logprob entropy** | Token-level uncertainty from logprobs | Fast, model-native |

**Recommended**: Combine logprob entropy (fast, first-pass) with HHEM (accurate, second-pass) for financial contexts.

### Prompt Injection Detection

| Technique | Approach | Performance |
|-----------|----------|-------------|
| **DeBERTa classifier** | Fine-tuned on injection datasets | 96%+ F1 |
| **PINT benchmark** (Lakera) | 4,314 inputs across 39 categories | Industry standard |
| **Instruction hierarchy** | Priority-based instruction separation | Reduces indirect injection |
| **Ensemble** | Multiple specialized classifiers voting | Highest accuracy |

### PII Detection

| Technique | Approach | Performance |
|-----------|----------|-------------|
| **Microsoft Presidio** | Open-source, pluggable analyzers | Good baseline |
| **GLiNER** | Zero-shot NER, 60+ categories | No retraining needed |
| **DeBERTa-v3 NER** | Fine-tuned for financial documents | 93% on real docs |
| **Regex patterns** | Fast, high precision for structured PII | Sub-1ms |

**Recommended**: Multi-layer -- regex first (SSNs, account numbers), GLiNER second (novel PII), DeBERTa third (financial context).

### Anomaly Detection

| Technique | Approach | Use Case |
|-----------|----------|----------|
| **Embedding drift** (PSI/KS tests) | Statistical distribution shift | Input/output quality degradation |
| **Token consumption monitoring** | Z-score on rolling window | Cost anomaly detection |
| **Behavioral baselines** | Per-agent usage patterns | Shadow AI, unusual activity |
| **FAISS similarity search** | Vector similarity for known attacks | Prompt injection variants |

### Multi-Turn Conversation Analysis

Crescendo attacks build context over multiple turns to eventually extract harmful content. Each individual turn appears benign.

**Feature opportunity**: Sliding window analysis across conversation turns. Track topic drift, escalation patterns, and information extraction attempts.

### Code Execution Safety

For agents that execute code:
- **gVisor/Firecracker**: Kernel-level sandboxing
- **AST-based static analysis**: Detect dangerous patterns before execution
- **Capability-based security**: Fine-grained permissions per tool

### Watermarking & Provenance

- **SynthID-Text** (DeepMind): Statistical watermarking preserving output quality
- **C2PA**: Content provenance standard for verifying AI-generated content

---

## Competitive Landscape

### The 2024-2025 Acquisition Wave

| Acquirer | Target | Price | Date |
|----------|--------|-------|------|
| Cisco | Robust Intelligence | $400M | Oct 2024 |
| Palo Alto Networks | Protect AI | $500-700M | Apr 2025 |
| Check Point | Lakera | $300M | Nov 2025 |
| CrowdStrike | Pangea | $260M | Sep 2025 |
| SentinelOne | Prompt Security | $180-250M | Aug 2025 |
| F5 | CalypsoAI | $180M | Sep 2025 |
| Cato Networks | Aim Security | Undisclosed | Sep 2025 |
| Apple | WhyLabs | Undisclosed | Jan 2025 |

**Impact**: All acquired products absorbed into massive enterprise platforms. They become features, not products. Enterprise platforms have 6-12 month procurement cycles. Mid-market fintechs need solutions deployable in days.

### Remaining Independent Competitors

| Company | Funding | Focus | Threat Level |
|---------|---------|-------|-------------|
| **Noma Security** | $100M | Full OWASP 9/9, enterprise-only | HIGH |
| **Lasso Security** | $28M | LLM gateway, MCP security, SIEM integration | MEDIUM |
| **Arthur AI** | $63M | LLM firewall (no funding since 2022) | LOW |
| **Guardrails AI** | $7.5M | Open-source framework, not a platform | LOW |
| **Portkey AI** | ~$3M | Gateway + observability, horizontal | MEDIUM |

### Platform Vendor Competitors

| Vendor | Product | Pricing | Key Capability |
|--------|---------|---------|---------------|
| Google Cloud | Model Armor | $0.10/1M tokens | Generic screening, PII, injection |
| Cloudflare | Firewall for AI | Free | Basic guardrails on edge network |
| NVIDIA | NeMo Guardrails | Free (OSS) | Declarative guardrail language |

### AgentGuard Feature Advantage Matrix

| Capability | AgentGuard | Competitors |
|-----------|-----------|-------------|
| Six detection categories | YES (unique) | No one covers all 6 |
| Fintech compliance detectors (SOX, PCI-DSS, FFIEC, NYDFS-500, DORA) | YES (unique) | No competitor |
| Full incident lifecycle (detect -> investigate -> resolve -> audit) | YES | Competitors stop at detection |
| Self-serve $99/mo | YES | Most enterprise-only |
| Proxy-native architecture | YES | Most are SDKs/APIs |
| Cost anomaly detection | YES (unique) | No competitor |
| Loop detection | YES (unique) | No competitor |

### Priority Feature Gaps

| Gap | Who Has It | Priority |
|-----|-----------|----------|
| SIEM/SOAR integration | Lasso | P1 |
| MCP protocol security | Prompt Security, Lasso | P1 |
| Sub-30ms latency guarantee | Pangea | P1 |
| 50+ PII types | Pangea | P1 |
| Indirect injection (PDFs/URLs) | Lakera | P1 |
| Shadow AI discovery | Pangea, Noma | P2 |
| Red teaming | Protect AI, Cisco | P2 |
| Supply chain scanning | Protect AI | P3 |

---

## Regulatory & Compliance Landscape

### Enforcement Timeline (Urgency Order)

| Framework | Enforcement Date | Penalty | Status |
|-----------|-----------------|---------|--------|
| DORA | Jan 17, 2025 | Up to 2% global turnover | **NOW ENFORCED** |
| PCI DSS 4.0 | Mar 31, 2025 | Varies by acquirer | **NOW ENFORCED** |
| SR 11-7 (Fed Reserve MRM) | Continuous | Supervisory actions | **NOW ENFORCED** |
| FINRA Rule 3110 | Continuous | Fines, censure | **NOW ENFORCED** |
| SEC AI Examinations | FY 2026 | Enforcement actions | **NOW ACTIVE** |
| Illinois HB 3773 | Jan 1, 2026 | Private right of action | APPROACHING |
| Texas TRAIGA | Jan 1, 2026 | Varies | APPROACHING |
| Colorado SB 205 | Jun 30, 2026 | $20K/violation | APPROACHING |
| EU AI Act (high-risk) | Aug 2, 2026 | Up to EUR 35M / 7% turnover | APPROACHING |

### EU AI Act Key Requirements

Financial AI classified as **high-risk** (credit scoring, loan approval, fraud detection, AML). Requirements:
- **Art. 9**: Risk management system throughout lifecycle
- **Art. 10**: Data governance for training and inference
- **Art. 12**: Automatic logging with 10-year retention
- **Art. 14**: Human oversight capabilities
- **Art. 15**: Accuracy, robustness, cybersecurity

AgentGuard's proxy captures every LLM interaction -- the exact data required for Art. 12 logging.

### NIST AI 600-1 (GenAI Risk Profile)

12 unique generative AI risks mapped to NIST AI RMF:
1. CBRN information generation
2. **Confabulation (hallucination)**
3. Data privacy
4. **Environmental impact**
5. Harmful bias
6. **Homogenization effects**
7. Human-AI configuration
8. **Information integrity**
9. **Information security (prompt injection)**
10. Intellectual property
11. Obscene/degrading content
12. Value chain risks

AgentGuard's 6 detection categories map to risks #2, #3, #5, #7, #8, #9.

### DORA (Already Enforceable)

Five pillars relevant to AgentGuard:
1. **ICT Risk Management**: Anomaly detection across LLM traffic
2. **Incident Reporting**: 24h/72h/1mo reporting timelines
3. **Resilience Testing**: Red teaming evidence
4. **Third-Party Oversight**: Monitor LLM API performance/security
5. **Information Sharing**: Anonymized threat intelligence

### SR 11-7 (Model Risk Management)

Federal Reserve/OCC guidance treating AI models as "models" requiring:
- Pre-deployment validation
- Ongoing monitoring (real-time performance tracking)
- Outcomes analysis
- Comprehensive documentation

AgentGuard's proxy provides continuous monitoring evidence that satisfies SR 11-7.

### SOC 2 for AI

Trust Services Criteria applied to AI:
- **Security**: Prompt injection defense
- **Processing Integrity**: Hallucination detection, output validation
- **Confidentiality**: PII leak detection
- **Privacy**: Data exposure monitoring
- **Availability**: Cost anomaly detection (DoS)

### ISO 42001 (AI Management System)

First certifiable international standard for AI management. 76% of organizations plan to pursue certification. AgentGuard can map detection categories to ISO 42001 controls for continuous compliance evidence.

---

## Cross-Framework Compliance Matrix

| AgentGuard Detector | EU AI Act | NIST 600-1 | SR 11-7 | DORA | SOC 2 | OWASP LLM | MITRE ATLAS |
|----|----|----|----|----|----|----|-----|
| **Hallucination** | Art. 9, 15 | #2 Confab | Ongoing Monitor | Pillar 1 | Processing Integrity | LLM09 | Confabulation |
| **PII Leak** | Art. 10 | #4 Privacy | Documentation | Pillar 2 | Privacy, Confidentiality | LLM02 | Exfiltration |
| **Compliance** | Art. 9 | #6 Bias, #10 IP | Validation | Pillar 1 | Processing Integrity | LLM05 | n/a |
| **Cost Anomaly** | Art. 72 | #5 Environment | Monitoring | Pillar 1 | Availability | LLM10 | Resource DoS |
| **Loop Detection** | Art. 14 | #7 Human-AI | Monitoring | Pillar 3 | Availability | LLM06 | Agent loops |
| **Prompt Injection** | Art. 15 | #9 Security | Validation | Pillar 2 | Security | LLM01 | 14+ techniques |

---

## Strategic Positioning

### AgentGuard's Unique Position

1. **Independence** -- 9 of 14 competitors acquired. Remaining independents are either enterprise-only (Noma), general-purpose (Lasso), stagnant (Arthur), or frameworks (Guardrails AI).

2. **Fintech Vertical** -- No competitor has purpose-built SOX, PCI-DSS, FFIEC, NYDFS-500, DORA, or EU AI Act compliance detectors.

3. **Six Detection Categories** -- No single competitor covers hallucination + PII + compliance + cost anomaly + loop detection + prompt injection.

4. **Proxy-Native Architecture** -- Simplest integration model (swap base URL). Most competitors are SDKs or API layers.

5. **Self-Serve SaaS** -- $99/mo entry point vs $50K+/year for enterprise alternatives. Targets underserved mid-market fintech.

6. **Full Incident Lifecycle** -- Detection -> investigation -> resolution -> audit trail. Competitors stop at detection.

### Positioning Statement

> **AgentGuard: The AI agent incident response platform purpose-built for financial services.** Proxy-native architecture with fintech compliance detectors and full incident lifecycle management -- for the regulatory moment that demands it.

### Key Risks

1. **Noma Security** ($100M funding, targets financial services, enterprise-only)
2. **Palo Alto/Protect AI** (massive distribution, Gartner front-runner)
3. **Cisco AI Defense** (enterprise brand trust)
4. **Cloudflare Firewall for AI** (free, massive distribution, sets pricing floor)
5. **Portkey AI** (most architecturally similar, could add fintech features)

---

## Source Index

### Anthropic
- Constitutional AI research and classifier architecture
- Prompt injection defense in agentic systems
- Agent safety (computer use, espionage campaigns)
- Interpretability (circuit tracing, hallucination architecture)
- Evaluations: Bloom, Petri, SHADE-Arena

### OpenAI
- [Moderation API](https://developers.openai.com/api/docs/guides/moderation/)
- [gpt-oss-safeguard](https://openai.com/index/introducing-gpt-oss-safeguard/)
- [Instruction Hierarchy](https://arxiv.org/abs/2404.13208)
- [Model Spec](https://model-spec.openai.com/2025-12-18.html)
- [Detecting Scheming](https://openai.com/index/detecting-and-reducing-scheming-in-ai-models/)
- [Why Language Models Hallucinate](https://arxiv.org/abs/2509.04664)
- [Safe Completions](https://openai.com/index/gpt-5-safe-completions/)
- [Structured Outputs Bypass](https://blogs.cisco.com/security/bypassing-openais-structured-outputs-another-simple-jailbreak)
- [Prompt Injection "Here to Stay"](https://venturebeat.com/security/openai-admits-that-prompt-injection-is-here-to-stay)
- [Aardvark Security Agent](https://openai.com/index/introducing-aardvark/)

### Google DeepMind
- [Gemini Security Safeguards](https://deepmind.google/discover/blog/advancing-geminis-security-safeguards/)
- [ADK Safety Framework](https://google.github.io/adk-docs/safety/)
- [SAIF](https://saif.google/secure-ai-framework)
- [AGI Safety Paper](https://arxiv.org/abs/2504.01849)
- [Frontier Safety Framework v3.0](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/strengthening-our-frontier-safety-framework/frontier-safety-framework_3.pdf)
- [Dangerous Capability Evaluations](https://arxiv.org/abs/2403.13793)
- [CoT Monitorability](https://arxiv.org/abs/2507.05246)
- [Gemma Scope 2](https://deepmind.google/blog/gemma-scope-2-helping-the-ai-safety-community-deepen-understanding-of-complex-language-model-behavior/)
- [Model Armor](https://cloud.google.com/security/products/model-armor)
- [Big Sleep](https://projectzero.google/2024/10/from-naptime-to-big-sleep.html)
- [Sec-Gemini v1](https://security.googleblog.com/2025/04/google-launches-sec-gemini-v1-new.html)

### Regulatory
- [EU AI Act](https://artificialintelligenceact.eu/)
- [NIST AI 600-1](https://airc.nist.gov/Docs/1)
- [SR 11-7](https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm)
- [DORA](https://www.ibm.com/think/topics/digital-operational-resilience-act)
- [ISO 42001](https://www.iso.org/standard/42001)
- [OWASP LLM Top 10 2025](https://genai.owasp.org/llm-top-10/)
- [MITRE ATLAS](https://atlas.mitre.org/)

### Industry & Market
- [AI Security Startups $8.5B Funding](https://www.linkedin.com/pulse/what-85b-ai-security-funding-tells-leaders-builders-2026-columbus-tm0tc)
- [Gartner AI TRiSM Market Guide 2025](https://www.gartner.com/en/documents/6185655)
- [McKinsey $2T TAM](https://cybersecurityventures.com/ai-expands-2-trillion-total-addressable-market-for-cybersecurity-providers/)

### Detection Techniques
- [HHEM (Vectara)](https://huggingface.co/vectara/hallucination_evaluation_model)
- [SelfCheckGPT](https://arxiv.org/abs/2303.08896)
- [FActScore](https://arxiv.org/abs/2305.14251)
- [HaluGate](https://arxiv.org/abs/2412.12591)
- [Microsoft Presidio](https://github.com/microsoft/presidio)
- [GLiNER](https://github.com/urchade/GLiNER)
- [PINT Benchmark](https://github.com/lakeraai/pint-benchmark)
- [Hybrid NER for Financial PII (Nature 2025)](https://www.nature.com/articles/s41598-025-04971-9)
