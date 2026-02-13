'use client';

interface WelcomeStepProps {
  orgName: string;
  onNext: () => void;
}

export default function WelcomeStep({ orgName, onNext }: WelcomeStepProps) {
  return (
    <div className="text-center">
      <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
        <span className="text-3xl">&#128737;</span>
      </div>
      <h2 className="text-xl font-semibold text-foreground">
        Welcome to AgentGuard, {orgName}!
      </h2>
      <p className="mx-auto mt-3 max-w-md text-sm text-muted-foreground">
        We&apos;ll get you set up in under 5 minutes. Here&apos;s what we&apos;ll do:
      </p>

      <div className="mx-auto mt-8 max-w-sm space-y-4 text-left">
        {[
          { num: '1', label: 'Create a proxy endpoint', desc: 'Route your LLM traffic through AgentGuard' },
          { num: '2', label: 'Generate an API key', desc: 'Authenticate your application requests' },
          { num: '3', label: 'Send a test request', desc: 'See real-time PII detection in action' },
        ].map((item) => (
          <div key={item.num} className="flex items-start gap-3">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-white">
              {item.num}
            </span>
            <div>
              <p className="text-sm font-medium text-foreground">{item.label}</p>
              <p className="text-xs text-muted-foreground">{item.desc}</p>
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={onNext}
        className="mt-10 rounded-lg bg-primary px-8 py-2.5 text-sm font-medium text-white hover:bg-primary/80"
      >
        Get started
      </button>
    </div>
  );
}
