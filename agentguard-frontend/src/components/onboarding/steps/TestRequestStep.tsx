'use client';

import { useState } from 'react';
import { apiFetch } from '@/lib/api';

interface TestRequestStepProps {
  apiKey: string;
  endpointId: string;
  onNext: (incidentId: string | null) => void;
}

type TestState = 'idle' | 'sending' | 'success' | 'error';

export default function TestRequestStep({ apiKey, endpointId, onNext }: TestRequestStepProps) {
  const [state, setState] = useState<TestState>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  const handleTest = async () => {
    setState('sending');
    setErrorMsg('');

    try {
      const token = localStorage.getItem('accessToken');
      const res = await fetch('/api/v1/proxy/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`,
          'X-Endpoint-Id': endpointId,
        },
        body: JSON.stringify({
          model: 'gpt-4',
          messages: [
            {
              role: 'user',
              content: 'My SSN is 123-45-6789 and my email is test@example.com. What should I do?',
            },
          ],
        }),
      });

      if (!res.ok) {
        // Expected — the proxy may reject or the upstream may not be configured.
        // Still check for incidents created by detection.
      }

      // Wait for detection to process
      await new Promise((r) => setTimeout(r, 2500));

      // Check if an incident was created
      try {
        const incidents = await apiFetch<{ items: { id: string }[] }>(
          '/incidents/?limit=1&category=pii_leak',
          { headers: token ? { Authorization: `Bearer ${token}` } : undefined },
        );
        if (incidents.items.length > 0) {
          setState('success');
          onNext(incidents.items[0].id);
          return;
        }
      } catch {
        // Incident check failed, still mark success
      }

      setState('success');
      onNext(null);
    } catch (err) {
      setState('error');
      setErrorMsg(
        err instanceof Error ? err.message : 'Request failed. You can skip this step.',
      );
    }
  };

  if (state === 'sending') {
    return (
      <div className="flex flex-col items-center py-10">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
        <p className="mt-4 text-sm text-gray-600">
          Sending test request with PII data...
        </p>
        <p className="mt-1 text-xs text-gray-400">
          AgentGuard will detect the PII and create an incident
        </p>
      </div>
    );
  }

  if (state === 'success') {
    return (
      <div className="flex flex-col items-center py-10">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-green-100">
          <span className="text-2xl">&#10003;</span>
        </div>
        <p className="mt-4 text-sm font-medium text-gray-900">Test complete!</p>
        <p className="mt-1 text-xs text-gray-500">
          Check the incidents page to see detected PII.
        </p>
      </div>
    );
  }

  return (
    <div>
      <p className="text-sm text-gray-600">
        Send a test request containing PII data through the proxy. AgentGuard will detect the
        sensitive information and create an incident.
      </p>

      <div className="mt-4 rounded-lg bg-gray-50 p-4">
        <p className="text-xs font-medium text-gray-500">Test payload</p>
        <p className="mt-1 text-sm text-gray-700">
          &quot;My SSN is 123-45-6789 and my email is test@example.com&quot;
        </p>
      </div>

      {state === 'error' && (
        <div className="mt-4 rounded-lg bg-yellow-50 p-4">
          <p className="text-sm text-yellow-800">{errorMsg}</p>
          <p className="mt-1 text-xs text-yellow-600">
            This usually means no upstream LLM key is configured. You can skip this step.
          </p>
        </div>
      )}

      <div className="mt-6 flex gap-3">
        <button
          onClick={handleTest}
          className="rounded-lg bg-primary-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-primary-700"
        >
          Send test request
        </button>
        <button
          onClick={() => onNext(null)}
          className="rounded-lg border border-gray-300 px-6 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Skip this step
        </button>
      </div>
    </div>
  );
}
