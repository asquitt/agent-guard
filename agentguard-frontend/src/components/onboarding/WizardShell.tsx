'use client';

interface WizardShellProps {
  currentStep: number;
  totalSteps: number;
  title: string;
  description: string;
  onSkip: () => void;
  children: React.ReactNode;
}

export default function WizardShell({
  currentStep,
  totalSteps,
  title,
  description,
  onSkip,
  children,
}: WizardShellProps) {
  const progress = ((currentStep - 1) / (totalSteps - 1)) * 100;

  return (
    <div className="flex min-h-screen flex-col bg-muted/50">
      {/* Header */}
      <header className="border-b border-border bg-card px-6 py-4">
        <div className="mx-auto flex max-w-2xl items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xl font-bold text-primary">AgentGuard</span>
            <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
              Setup
            </span>
          </div>
          <button
            onClick={onSkip}
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Skip setup
          </button>
        </div>
      </header>

      {/* Progress bar */}
      <div className="bg-card px-6 pb-6">
        <div className="mx-auto max-w-2xl">
          <div className="flex items-center justify-between pt-4 text-xs text-muted-foreground">
            <span>Step {currentStep} of {totalSteps}</span>
            <span>{Math.round(progress)}% complete</span>
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary/100 transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Content */}
      <main className="flex flex-1 flex-col items-center px-6 py-10">
        <div className="w-full max-w-2xl">
          <h1 className="text-2xl font-bold text-foreground">{title}</h1>
          <p className="mt-2 text-sm text-muted-foreground">{description}</p>
          <div className="mt-8">{children}</div>
        </div>
      </main>
    </div>
  );
}
