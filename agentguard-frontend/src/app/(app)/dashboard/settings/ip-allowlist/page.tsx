'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import { apiFetch } from '@/lib/api';

interface IpAllowlistData {
  ips: string[];
  enabled: boolean;
}

async function getIpAllowlist(): Promise<IpAllowlistData> {
  return apiFetch<IpAllowlistData>('/organizations/current/ip-allowlist');
}

async function updateIpAllowlist(ips: string[]): Promise<IpAllowlistData> {
  return apiFetch<IpAllowlistData>('/organizations/current/ip-allowlist', {
    method: 'PUT',
    body: JSON.stringify({ ips }),
  });
}

const IP_REGEX = /^(\d{1,3}\.){3}\d{1,3}(\/\d{1,2})?$/;
const IPV6_REGEX = /^[0-9a-fA-F:]+(\/(12[0-8]|[1-9]\d?))?$/;

function isValidIpEntry(value: string): boolean {
  return IP_REGEX.test(value) || IPV6_REGEX.test(value);
}

export default function IpAllowlistPage() {
  const queryClient = useQueryClient();
  const [newIp, setNewIp] = useState('');
  const [error, setError] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['ipAllowlist'],
    queryFn: getIpAllowlist,
  });

  const mutation = useMutation({
    mutationFn: updateIpAllowlist,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ipAllowlist'] });
      setError('');
    },
    onError: (err: Error) => setError(err.message),
  });

  const ips = data?.ips ?? [];

  function handleAdd() {
    const trimmed = newIp.trim();
    if (!trimmed) return;
    if (!isValidIpEntry(trimmed)) {
      setError('Invalid IP address or CIDR range');
      return;
    }
    if (ips.includes(trimmed)) {
      setError('IP already in allowlist');
      return;
    }
    mutation.mutate([...ips, trimmed]);
    setNewIp('');
  }

  function handleRemove(ip: string) {
    mutation.mutate(ips.filter((i) => i !== ip));
  }

  function handleClear() {
    mutation.mutate([]);
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">IP Allowlisting</h1>
        <p className="text-sm text-gray-500">
          Restrict proxy access to specific IP addresses or CIDR ranges
        </p>
      </div>

      <div className="mb-6 rounded-xl border border-gray-200 bg-white p-6">
        <div className="mb-4 flex items-center gap-3">
          <div
            className={clsx(
              'inline-flex rounded-full px-3 py-1 text-xs font-medium',
              data?.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500',
            )}
          >
            {data?.enabled ? 'Active' : 'Disabled (all IPs allowed)'}
          </div>
          {ips.length > 0 && (
            <span className="text-xs text-gray-500">{ips.length} IP{ips.length !== 1 ? 's' : ''} configured</span>
          )}
        </div>

        <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-xs text-yellow-800 mb-4">
          <strong>Warning:</strong> Adding IPs will restrict proxy access. Ensure your current IP is included
          or you may lose proxy connectivity. Dashboard access is not affected.
        </div>

        {/* Add IP form */}
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={newIp}
            onChange={(e) => { setNewIp(e.target.value); setError(''); }}
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
            placeholder="e.g. 192.168.1.0/24 or 10.0.0.5"
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
          <button
            onClick={handleAdd}
            disabled={!newIp.trim() || mutation.isPending}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-500 disabled:opacity-50"
          >
            Add
          </button>
        </div>

        {error && <p className="mb-4 text-xs text-red-600">{error}</p>}

        {/* IP list */}
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
          </div>
        ) : ips.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 py-8 text-center text-sm text-gray-500">
            No IPs configured — all addresses can access the proxy
          </div>
        ) : (
          <div className="space-y-2">
            {ips.map((ip) => (
              <div
                key={ip}
                className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-4 py-2.5"
              >
                <code className="text-sm text-gray-900">{ip}</code>
                <button
                  onClick={() => handleRemove(ip)}
                  disabled={mutation.isPending}
                  className="text-xs font-medium text-red-600 hover:text-red-500 disabled:opacity-50"
                >
                  Remove
                </button>
              </div>
            ))}
            <div className="pt-2">
              <button
                onClick={handleClear}
                disabled={mutation.isPending}
                className="text-xs font-medium text-gray-500 hover:text-gray-700"
              >
                Clear all &amp; disable allowlist
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
