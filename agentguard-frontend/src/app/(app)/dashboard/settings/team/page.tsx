'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import {
  listMembers,
  listRoles,
  updateMemberRole,
  removeMember,
  inviteMember,
} from '@/lib/api/organizations';
import type { Member, RoleInfo } from '@/lib/api/organizations';

const ROLE_BADGE_COLORS: Record<string, string> = {
  owner: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  admin: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  member: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
  viewer: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
};

export default function TeamSettingsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('member');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editRole, setEditRole] = useState('');
  const [removingMember, setRemovingMember] = useState<Member | null>(null);

  const { data: members, isLoading } = useQuery({
    queryKey: ['team-members'],
    queryFn: () => listMembers(),
  });

  const { data: rolesData } = useQuery({
    queryKey: ['team-roles'],
    queryFn: listRoles,
  });

  const inviteMutation = useMutation({
    mutationFn: ({ email, role }: { email: string; role: string }) =>
      inviteMember(email, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team-members'] });
      setShowInvite(false);
      setInviteEmail('');
      setInviteRole('member');
    },
  });

  const updateRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      updateMemberRole(userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team-members'] });
      setEditingId(null);
    },
  });

  const removeMutation = useMutation({
    mutationFn: removeMember,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['team-members'] }),
  });

  const roles = rolesData?.roles ?? [];
  const isAdmin = user?.role === 'admin' || user?.role === 'owner';

  function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    inviteMutation.mutate({ email: inviteEmail, role: inviteRole });
  }

  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-6">
        <Link
          href="/dashboard/settings"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          &larr; Settings
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-foreground">
          Team Management
        </h1>
        <p className="text-sm text-muted-foreground">
          Invite members, manage roles, and control access
        </p>
      </div>

      {/* Members List */}
      <div className="mb-6 rounded-xl border border-border bg-card p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">
            Team Members ({members?.total ?? 0})
          </h2>
          {isAdmin && (
            <button
              onClick={() => setShowInvite(!showInvite)}
              className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
            >
              {showInvite ? 'Cancel' : '+ Invite Member'}
            </button>
          )}
        </div>

        {/* Invite Form */}
        {showInvite && (
          <form
            onSubmit={handleInvite}
            className="mb-6 space-y-4 rounded-lg border border-border bg-muted/50 p-4"
          >
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="sm:col-span-2">
                <label className="mb-1 block text-xs font-medium text-foreground">
                  Email Address
                </label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="colleague@company.com"
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
                  required
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-foreground">
                  Role
                </label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
                >
                  {roles
                    .filter((r) => r.role !== 'owner')
                    .map((r) => (
                      <option key={r.role} value={r.role}>
                        {r.role.charAt(0).toUpperCase() + r.role.slice(1)}
                      </option>
                    ))}
                </select>
              </div>
            </div>
            {inviteMutation.isError && (
              <p className="text-xs text-red-500">
                {(inviteMutation.error as Error)?.message ?? 'Failed to invite'}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowInvite(false)}
                className="rounded-md border border-border px-3 py-1.5 text-xs text-foreground hover:bg-muted"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={inviteMutation.isPending}
                className="rounded-md bg-primary px-4 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {inviteMutation.isPending ? 'Inviting...' : 'Send Invite'}
              </button>
            </div>
          </form>
        )}

        {/* Members Table */}
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading...</p>
        ) : members?.items.length === 0 ? (
          <p className="text-sm text-muted-foreground">No team members found.</p>
        ) : (
          <div className="space-y-2">
            {members?.items.map((m: Member) => (
              <div
                key={m.id}
                className="flex items-center justify-between rounded-lg border border-border p-4"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                      {m.name?.charAt(0).toUpperCase() ?? '?'}
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-foreground">
                        {m.name}
                        {m.id === user?.id && (
                          <span className="ml-1.5 text-xs text-muted-foreground">(you)</span>
                        )}
                      </p>
                      <p className="truncate text-xs text-muted-foreground">{m.email}</p>
                    </div>
                  </div>
                </div>
                <div className="ml-4 flex items-center gap-2">
                  {editingId === m.id ? (
                    <>
                      <select
                        value={editRole}
                        onChange={(e) => setEditRole(e.target.value)}
                        className="rounded-md border border-border bg-background px-2 py-1 text-xs text-foreground"
                      >
                        {roles.map((r) => (
                          <option key={r.role} value={r.role}>
                            {r.role.charAt(0).toUpperCase() + r.role.slice(1)}
                          </option>
                        ))}
                      </select>
                      <button
                        onClick={() =>
                          updateRoleMutation.mutate({ userId: m.id, role: editRole })
                        }
                        disabled={updateRoleMutation.isPending}
                        className="rounded-md bg-primary px-2 py-1 text-xs text-primary-foreground hover:bg-primary/90"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="rounded-md border border-border px-2 py-1 text-xs text-foreground hover:bg-muted"
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs ${
                          ROLE_BADGE_COLORS[m.role] ?? ROLE_BADGE_COLORS.member
                        }`}
                      >
                        {m.role}
                      </span>
                      {!m.isActive && (
                        <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-400">
                          Inactive
                        </span>
                      )}
                      {isAdmin && m.id !== user?.id && (
                        <>
                          <button
                            onClick={() => {
                              setEditingId(m.id);
                              setEditRole(m.role);
                            }}
                            className="rounded-md border border-border px-2 py-1 text-xs text-foreground hover:bg-muted"
                          >
                            Edit Role
                          </button>
                          <button
                            onClick={() => setRemovingMember(m)}
                            className="rounded-md border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-900/20"
                          >
                            Remove
                          </button>
                        </>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Roles & Permissions */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h2 className="mb-3 text-sm font-semibold text-foreground">
          Roles & Permissions
        </h2>
        <div className="space-y-4">
          {roles.map((r: RoleInfo) => (
            <div key={r.role}>
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    ROLE_BADGE_COLORS[r.role] ?? ROLE_BADGE_COLORS.member
                  }`}
                >
                  {r.role}
                </span>
              </div>
              <div className="mt-1 flex flex-wrap gap-1">
                {r.permissions.map((p) => (
                  <span
                    key={p}
                    className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
                  >
                    {p}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <ConfirmDialog
        open={!!removingMember}
        title="Remove team member"
        description={`Are you sure you want to remove ${removingMember?.name ?? 'this member'} from the team? They will lose access immediately.`}
        confirmLabel="Remove"
        variant="danger"
        loading={removeMutation.isPending}
        onConfirm={() => {
          if (removingMember) {
            removeMutation.mutate(removingMember.id, {
              onSuccess: () => setRemovingMember(null),
            });
          }
        }}
        onCancel={() => setRemovingMember(null)}
      />
    </div>
  );
}
