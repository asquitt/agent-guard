'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { updateOrgSettings } from '@/lib/api';
import WizardShell from '@/components/onboarding/WizardShell';
import WelcomeStep from '@/components/onboarding/steps/WelcomeStep';
import ProxyEndpointStep from '@/components/onboarding/steps/ProxyEndpointStep';
import ApiKeyStep from '@/components/onboarding/steps/ApiKeyStep';
import IntegrationStep from '@/components/onboarding/steps/IntegrationStep';
import TestRequestStep from '@/components/onboarding/steps/TestRequestStep';
import CompletionStep from '@/components/onboarding/steps/CompletionStep';

const TOTAL_STEPS = 6;

const STEP_META: Record<number, { title: string; description: string }> = {
  1: { title: 'Welcome', description: 'Let\'s get your account set up' },
  2: { title: 'Create Proxy Endpoint', description: 'Choose your LLM provider to route traffic through AgentGuard' },
  3: { title: 'Generate API Key', description: 'Create credentials for your application' },
  4: { title: 'Integrate Your App', description: 'Add a few lines of code to start monitoring' },
  5: { title: 'Test Detection', description: 'Send a test request to see AgentGuard in action' },
  6: { title: 'Setup Complete', description: 'You\'re ready to go!' },
};

export default function OnboardingPage() {
  const router = useRouter();
  const { organization, fetchMe } = useAuth();

  const [step, setStep] = useState(1);
  const [endpointId, setEndpointId] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [incidentId, setIncidentId] = useState<string | null>(null);

  // Redirect if onboarding already completed
  useEffect(() => {
    if (organization?.settings?.onboardingCompleted) {
      router.replace('/dashboard');
    }
  }, [organization, router]);

  const finishOnboarding = useCallback(async () => {
    try {
      await updateOrgSettings({ onboardingCompleted: true });
      await fetchMe();
    } catch {
      // Non-blocking — user can still navigate
    }
  }, [fetchMe]);

  const handleSkip = async () => {
    await finishOnboarding();
    router.push('/dashboard');
  };

  const meta = STEP_META[step];

  return (
    <WizardShell
      currentStep={step}
      totalSteps={TOTAL_STEPS}
      title={meta.title}
      description={meta.description}
      onSkip={handleSkip}
    >
      {step === 1 && (
        <WelcomeStep
          orgName={organization?.name ?? 'your team'}
          onNext={() => setStep(2)}
        />
      )}
      {step === 2 && (
        <ProxyEndpointStep
          onNext={(id) => { setEndpointId(id); setStep(3); }}
        />
      )}
      {step === 3 && (
        <ApiKeyStep
          onNext={(key) => { setApiKey(key); setStep(4); }}
        />
      )}
      {step === 4 && (
        <IntegrationStep
          apiKey={apiKey}
          endpointId={endpointId}
          onNext={() => setStep(5)}
        />
      )}
      {step === 5 && (
        <TestRequestStep
          apiKey={apiKey}
          endpointId={endpointId}
          onNext={(id) => { setIncidentId(id); setStep(6); }}
        />
      )}
      {step === 6 && (
        <CompletionStep
          incidentId={incidentId}
          onFinish={finishOnboarding}
        />
      )}
    </WizardShell>
  );
}
