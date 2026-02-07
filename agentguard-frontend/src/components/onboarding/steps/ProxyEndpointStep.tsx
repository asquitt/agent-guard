'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { createProxyEndpoint } from '@/lib/api';

const PROVIDERS = [
  {
    id: 'openai',
    name: 'OpenAI',
    url: 'https://api.openai.com/v1',
    desc: 'GPT-4, GPT-3.5, and other OpenAI models',
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    url: 'https://api.anthropic.com/v1',
    desc: 'Claude and other Anthropic models',
  },
] as const;

interface ProxyEndpointStepProps {
  onNext: (endpointId: string) => void;
}

export default function ProxyEndpointStep({ onNext }: ProxyEndpointStepProps) {
  const [selected, setSelected] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (provider: typeof PROVIDERS[number]) =>
      createProxyEndpoint({
        name: `${provider.name} Proxy`,
        provider: provider.id,
        target_url: provider.url,
      }),
    onSuccess: (data) => onNext(data.id),
  });

  const handleCreate = () => {
    const provider = PROVIDERS.find((p) => p.id === selected);
    if (provider) mutation.mutate(provider);
  };

  return (
    <div>
      <div className="grid grid-cols-2 gap-4">
        {PROVIDERS.map((provider) => (
          <button
            key={provider.id}
            onClick={() => setSelected(provider.id)}
            className={`rounded-xl border-2 p-5 text-left transition-colors ${
              selected === provider.id
                ? 'border-primary-500 bg-primary-50'
                : 'border-gray-200 bg-white hover:border-gray-300'
            }`}
          >
            <p className="text-sm font-semibold text-gray-900">{provider.name}</p>
            <p className="mt-1 text-xs text-gray-500">{provider.desc}</p>
            <p className="mt-2 truncate text-xs font-mono text-gray-400">{provider.url}</p>
          </button>
        ))}
      </div>

      {mutation.isError && (
        <p className="mt-4 text-sm text-red-600">
          {mutation.error?.message || 'Failed to create endpoint'}
        </p>
      )}

      <button
        onClick={handleCreate}
        disabled={!selected || mutation.isPending}
        className="mt-6 rounded-lg bg-primary-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
      >
        {mutation.isPending ? 'Creating...' : 'Create endpoint'}
      </button>
    </div>
  );
}
