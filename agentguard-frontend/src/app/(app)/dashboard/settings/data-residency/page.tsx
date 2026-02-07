'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import { getDataResidency, updateDataResidency } from '@/lib/api';

const PROVIDERS = ['openai', 'anthropic', 'google_gemini', 'azure_openai', 'bedrock'] as const;

export default function DataResidencyPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['data-residency'],
    queryFn: getDataResidency,
  });

  const [primaryRegion, setPrimaryRegion] = useState('us-east-1');
  const [allowedRegions, setAllowedRegions] = useState<string[]>(['us-east-1']);
  const [enforceResidency, setEnforceResidency] = useState(false);
  const [encryptionKeyId, setEncryptionKeyId] = useState('');

  useEffect(() => {
    if (data?.config) {
      setPrimaryRegion(data.config.primaryRegion);
      setAllowedRegions(data.config.allowedRegions);
      setEnforceResidency(data.config.enforceResidency);
      setEncryptionKeyId(data.config.encryptionKeyId ?? '');
    }
  }, [data]);

  const mutation = useMutation({
    mutationFn: () =>
      updateDataResidency({
        primaryRegion,
        allowedRegions,
        enforceResidency,
        encryptionKeyId: encryptionKeyId.trim() || null,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['data-residency'] }),
  });

  const regions = data?.availableRegions ?? [];

  function toggleRegion(regionId: string) {
    setAllowedRegions((prev) =>
      prev.includes(regionId) ? prev.filter((r) => r !== regionId) : [...prev, regionId],
    );
  }

  return (
    <div>
      <div className="mb-6">
        <button
          onClick={() => router.push('/dashboard/settings')}
          className="mb-2 text-xs text-primary-600 hover:text-primary-500"
        >
          &larr; Back to Settings
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Data Residency & Sovereignty</h1>
        <p className="text-sm text-gray-500">
          Configure where your data is stored and processed for regulatory compliance
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Primary region */}
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-sm font-semibold text-gray-900">Primary Data Region</h2>
            <p className="mb-3 text-xs text-gray-500">
              The primary region where your data is stored and processed.
            </p>
            <select
              value={primaryRegion}
              onChange={(e) => setPrimaryRegion(e.target.value)}
              className="w-full max-w-xs rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              {regions.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} ({r.country})
                </option>
              ))}
            </select>
          </div>

          {/* Allowed regions */}
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-sm font-semibold text-gray-900">Allowed Data Regions</h2>
            <p className="mb-3 text-xs text-gray-500">
              Select regions where your proxy traffic and data may be processed.
              At minimum, the primary region must be selected.
            </p>
            <div className="grid grid-cols-3 gap-3">
              {regions.map((r) => {
                const isSelected = allowedRegions.includes(r.id);
                const isPrimary = r.id === primaryRegion;
                return (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => !isPrimary && toggleRegion(r.id)}
                    disabled={isPrimary}
                    className={clsx(
                      'rounded-lg border px-4 py-3 text-left transition-colors',
                      isSelected
                        ? 'border-primary-300 bg-primary-50'
                        : 'border-gray-200 bg-gray-50 hover:bg-gray-100',
                      isPrimary && 'cursor-not-allowed opacity-60',
                    )}
                  >
                    <p className="text-sm font-medium text-gray-900">{r.name}</p>
                    <p className="text-xs text-gray-500">{r.country}</p>
                    {isPrimary && (
                      <span className="mt-1 inline-block rounded bg-primary-100 px-2 py-0.5 text-xs text-primary-700">
                        Primary
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Enforcement toggle */}
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-gray-900">Enforce Data Residency</h2>
                <p className="mt-1 text-xs text-gray-500">
                  When enabled, proxy requests to providers outside allowed regions will be blocked.
                  Violations will create compliance incidents.
                </p>
              </div>
              <button
                onClick={() => setEnforceResidency(!enforceResidency)}
                className={clsx(
                  'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                  enforceResidency ? 'bg-primary-600' : 'bg-gray-300',
                )}
              >
                <span
                  className={clsx(
                    'inline-block h-4 w-4 rounded-full bg-white transition-transform',
                    enforceResidency ? 'translate-x-6' : 'translate-x-1',
                  )}
                />
              </button>
            </div>
          </div>

          {/* BYOK encryption */}
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-sm font-semibold text-gray-900">
              Customer-Managed Encryption Key (BYOK)
            </h2>
            <p className="mb-3 text-xs text-gray-500">
              Provide your own KMS key ID for encrypting stored proxy data at rest.
              Leave empty to use platform-managed encryption.
            </p>
            <input
              value={encryptionKeyId}
              onChange={(e) => setEncryptionKeyId(e.target.value)}
              className="w-full max-w-lg rounded-lg border border-gray-300 px-3 py-2 text-sm"
              placeholder="arn:aws:kms:us-east-1:123456789:key/abc-def-..."
            />
          </div>

          {/* Provider allowlist per region */}
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-sm font-semibold text-gray-900">
              Allowed Providers by Region
            </h2>
            <p className="mb-3 text-xs text-gray-500">
              Available LLM providers for each allowed region. Providers not listed
              will be blocked when enforcement is enabled.
            </p>
            <div className="space-y-3">
              {allowedRegions.map((regionId) => {
                const region = regions.find((r) => r.id === regionId);
                return (
                  <div key={regionId} className="rounded-lg border border-gray-100 p-3">
                    <p className="mb-2 text-xs font-medium text-gray-700">
                      {region?.name ?? regionId}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {PROVIDERS.map((p) => (
                        <span
                          key={p}
                          className="rounded bg-blue-50 px-2 py-1 text-xs text-blue-700"
                        >
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Save */}
          <div className="flex gap-3">
            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="rounded-lg bg-primary-600 px-6 py-2 text-sm font-medium text-white hover:bg-primary-500 disabled:opacity-50"
            >
              {mutation.isPending ? 'Saving...' : 'Save Configuration'}
            </button>
            {mutation.isSuccess && (
              <span className="self-center text-xs text-green-600">Saved successfully</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
