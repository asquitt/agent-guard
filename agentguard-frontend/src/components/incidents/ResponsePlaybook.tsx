'use client';

import { useState } from 'react';
import { clsx } from 'clsx';
import { CheckCircle2, Circle, BookOpen, ChevronDown, ChevronRight } from 'lucide-react';

interface PlaybookStep {
  id: string;
  title: string;
  description: string;
}

interface Playbook {
  category: string;
  label: string;
  severity: string;
  steps: PlaybookStep[];
}

/**
 * Playbook definitions per incident category.
 * Each has ordered response steps SOC analysts should follow.
 */
const PLAYBOOKS: Record<string, Playbook> = {
  prompt_injection: {
    category: 'prompt_injection',
    label: 'Prompt Injection Response',
    severity: 'high',
    steps: [
      { id: 'pi-1', title: 'Review injected content', description: 'Examine the proxy request payload for injected instructions or system prompt overrides.' },
      { id: 'pi-2', title: 'Verify action was blocked', description: 'Confirm the detection pipeline blocked or redacted the malicious payload before it reached the LLM.' },
      { id: 'pi-3', title: 'Check for data exfiltration', description: 'Review the LLM response for any leaked system prompts, API keys, or internal data.' },
      { id: 'pi-4', title: 'Identify attack vector', description: 'Determine if the injection came via user input, tool output, or indirect prompt injection from external data.' },
      { id: 'pi-5', title: 'Update detector rules', description: 'Add the injection pattern to detector rules to prevent similar future attacks.' },
      { id: 'pi-6', title: 'Escalate if needed', description: 'If data was leaked or the agent took unauthorized actions, escalate to the security team.' },
    ],
  },
  pii_leak: {
    category: 'pii_leak',
    label: 'PII Leak Response',
    severity: 'critical',
    steps: [
      { id: 'pii-1', title: 'Identify exposed data', description: 'Determine what PII was leaked: names, SSNs, account numbers, emails, etc.' },
      { id: 'pii-2', title: 'Verify redaction applied', description: 'Check if the detection pipeline successfully redacted the PII from the response.' },
      { id: 'pii-3', title: 'Assess exposure scope', description: 'Determine who had access to the unredacted response and whether it was stored or forwarded.' },
      { id: 'pii-4', title: 'Initiate breach protocol', description: 'If PII was exposed externally, initiate your organization\'s data breach notification procedure.' },
      { id: 'pii-5', title: 'Review data handling policies', description: 'Verify that the agent\'s system prompt includes clear instructions to avoid handling PII.' },
      { id: 'pii-6', title: 'File compliance report', description: 'Document the incident for regulatory compliance (GDPR, CCPA, etc.).' },
    ],
  },
  hallucination: {
    category: 'hallucination',
    label: 'Hallucination Response',
    severity: 'medium',
    steps: [
      { id: 'hal-1', title: 'Review hallucinated content', description: 'Identify the specific factual claims that were fabricated by the LLM.' },
      { id: 'hal-2', title: 'Assess impact', description: 'Determine if the hallucinated content was used for decision-making, customer communication, or financial analysis.' },
      { id: 'hal-3', title: 'Check downstream actions', description: 'Verify that no automated actions were taken based on the incorrect information.' },
      { id: 'hal-4', title: 'Adjust confidence thresholds', description: 'Tighten the hallucination detector sensitivity in detector settings.' },
      { id: 'hal-5', title: 'Add grounding context', description: 'Ensure the agent has access to verified data sources to reduce hallucination risk.' },
    ],
  },
  compliance: {
    category: 'compliance',
    label: 'Compliance Violation Response',
    severity: 'critical',
    steps: [
      { id: 'comp-1', title: 'Identify violated regulation', description: 'Determine which regulation was violated: SOX, PCI-DSS, FFIEC, NYDFS-500, DORA, or EU AI Act.' },
      { id: 'comp-2', title: 'Review agent output', description: 'Examine the response for unauthorized financial advice, missing disclaimers, or prohibited actions.' },
      { id: 'comp-3', title: 'Document the violation', description: 'Create a detailed record of the violation for audit trail purposes.' },
      { id: 'comp-4', title: 'Notify compliance team', description: 'Alert the compliance officer and legal team about the potential regulatory violation.' },
      { id: 'comp-5', title: 'Implement guardrails', description: 'Add or strengthen compliance-specific detector rules to prevent recurrence.' },
      { id: 'comp-6', title: 'Schedule audit review', description: 'Schedule a review of the agent\'s compliance configuration with the governance team.' },
    ],
  },
  cost_anomaly: {
    category: 'cost_anomaly',
    label: 'Cost Anomaly Response',
    severity: 'medium',
    steps: [
      { id: 'cost-1', title: 'Review token usage', description: 'Check the proxy request for unusually high token counts or expensive model usage.' },
      { id: 'cost-2', title: 'Identify root cause', description: 'Determine if the anomaly is from a looping agent, large context window, or misconfigured model.' },
      { id: 'cost-3', title: 'Check for abuse', description: 'Verify the request came from an authorized user/agent and not from credential compromise.' },
      { id: 'cost-4', title: 'Adjust cost limits', description: 'Update per-request or per-agent cost limits in the proxy configuration.' },
    ],
  },
  loop: {
    category: 'loop',
    label: 'Loop Detection Response',
    severity: 'medium',
    steps: [
      { id: 'loop-1', title: 'Verify loop detected', description: 'Confirm the agent is producing repeated outputs or stuck in a recursive tool-call cycle.' },
      { id: 'loop-2', title: 'Check agent state', description: 'Review the conversation history and tool call chain that led to the loop.' },
      { id: 'loop-3', title: 'Terminate the session', description: 'If the agent is still running, terminate the session to prevent further cost and data impact.' },
      { id: 'loop-4', title: 'Adjust loop thresholds', description: 'Fine-tune the loop detector\'s repetition count and similarity thresholds.' },
    ],
  },
  toxicity: {
    category: 'toxicity',
    label: 'Toxicity Response',
    severity: 'high',
    steps: [
      { id: 'tox-1', title: 'Review toxic content', description: 'Examine the flagged content for hate speech, harassment, bias, or harmful material.' },
      { id: 'tox-2', title: 'Assess audience impact', description: 'Determine if the content reached end users, customers, or was intercepted by the pipeline.' },
      { id: 'tox-3', title: 'Report to trust & safety', description: 'Escalate the content to your organization\'s trust and safety or HR team.' },
      { id: 'tox-4', title: 'Review system prompt', description: 'Ensure the agent\'s system prompt includes clear content policy guidelines.' },
    ],
  },
};

/** Default playbook for categories without a specific one */
const DEFAULT_PLAYBOOK: PlaybookStep[] = [
  { id: 'def-1', title: 'Review the incident details', description: 'Examine the detection context, proxy request, and agent response.' },
  { id: 'def-2', title: 'Assess severity and impact', description: 'Determine the blast radius and whether any downstream systems were affected.' },
  { id: 'def-3', title: 'Take corrective action', description: 'Resolve, dismiss, or escalate based on your assessment.' },
  { id: 'def-4', title: 'Update detection rules', description: 'Adjust detector thresholds or rules to improve future detection.' },
];

export function ResponsePlaybook({ category }: { category: string }) {
  const playbook = PLAYBOOKS[category];
  const steps = playbook?.steps ?? DEFAULT_PLAYBOOK;
  const label = playbook?.label ?? 'Incident Response';
  const [completed, setCompleted] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState(true);

  function toggleStep(id: string) {
    setCompleted((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const progress = steps.length > 0 ? Math.round((completed.size / steps.length) * 100) : 0;

  return (
    <div className="rounded-xl border border-border bg-card">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between border-b border-border px-6 py-4"
      >
        <div className="flex items-center gap-3">
          <BookOpen className="h-4 w-4 text-primary" />
          <h2 className="text-lg font-semibold text-foreground">{label}</h2>
        </div>
        <div className="flex items-center gap-3">
          {progress > 0 && (
            <span className="text-xs text-muted-foreground">{progress}% complete</span>
          )}
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-6 py-4">
          {/* Progress bar */}
          {steps.length > 0 && (
            <div className="mb-4">
              <div className="h-1.5 w-full rounded-full bg-muted">
                <div
                  className="h-1.5 rounded-full bg-primary transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          <div className="space-y-2">
            {steps.map((step, i) => {
              const isDone = completed.has(step.id);
              return (
                <button
                  key={step.id}
                  onClick={() => toggleStep(step.id)}
                  className={clsx(
                    'flex w-full items-start gap-3 rounded-lg px-3 py-2.5 text-left transition-colors',
                    isDone ? 'bg-green-500/5' : 'hover:bg-muted/50',
                  )}
                >
                  <div className="mt-0.5 shrink-0">
                    {isDone ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : (
                      <Circle className="h-4 w-4 text-muted-foreground/40" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={clsx(
                      'text-sm font-medium',
                      isDone ? 'text-muted-foreground line-through' : 'text-foreground',
                    )}>
                      {i + 1}. {step.title}
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {step.description}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
