'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { createApiKey } from '@/lib/api';

interface ApiKeyStepProps {
  onNext: (apiKey: string) => void;
}

export default function ApiKeyStep({ onNext }: ApiKeyStepProps) {
  const [key, setKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const mutation = useMutation({
    mutationFn: () => createApiKey({ name: 'Onboarding Key' }),
    onSuccess: (data) => setKey(data.key),
  });

  const handleCopy = async () => {
    if (!key) return;
    await navigator.clipboard.writeText(key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!key) {
    return (
      <div className="text-center">
        <p className="text-sm text-gray-600">
          Generate an API key to authenticate your requests through the proxy.
        </p>
        {mutation.isError && (
          <p className="mt-3 text-sm text-red-600">
            {mutation.error?.message || 'Failed to generate key'}
          </p>
        )}
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="mt-6 rounded-lg bg-primary-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          {mutation.isPending ? 'Generating...' : 'Generate API Key'}
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
        <p className="text-sm font-medium text-yellow-800">
          Save this key now — you won&apos;t be able to see it again.
        </p>
      </div>

      <div className="mt-4 flex items-center gap-2 rounded-lg bg-gray-900 p-4">
        <code className="flex-1 truncate text-sm text-green-400">{key}</code>
        <button
          onClick={handleCopy}
          className="shrink-0 rounded-md bg-gray-700 px-3 py-1.5 text-xs font-medium text-gray-200 hover:bg-gray-600"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>

      <button
        onClick={() => onNext(key)}
        className="mt-6 rounded-lg bg-primary-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-primary-700"
      >
        Continue
      </button>
    </div>
  );
}
