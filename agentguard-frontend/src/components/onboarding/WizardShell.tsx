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
    <div className="flex min-h-screen flex-col bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="mx-auto flex max-w-2xl items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xl font-bold text-primary-600">AgentGuard</span>
            <span className="rounded-full bg-primary-100 px-2.5 py-0.5 text-xs font-medium text-primary-700">
              Setup
            </span>
          </div>
          <button
            onClick={onSkip}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Skip setup
          </button>
        </div>
      </header>

      {/* Progress bar */}
      <div className="bg-white px-6 pb-6">
        <div className="mx-auto max-w-2xl">
          <div className="flex items-center justify-between pt-4 text-xs text-gray-500">
            <span>Step {currentStep} of {totalSteps}</span>
            <span>{Math.round(progress)}% complete</span>
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-full rounded-full bg-primary-500 transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Content */}
      <main className="flex flex-1 flex-col items-center px-6 py-10">
        <div className="w-full max-w-2xl">
          <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
          <p className="mt-2 text-sm text-gray-500">{description}</p>
          <div className="mt-8">{children}</div>
        </div>
      </main>
    </div>
  );
}
