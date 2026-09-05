import { beforeEach, describe, expect, it, vi } from 'vitest';

import { registerApi } from '@/lib/api/auth';

describe('registerApi', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('sends the server-enforced evaluation acceptance and access code', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({ access_token: 'access', refresh_token: 'refresh' }),
        { status: 201, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    await registerApi({
      email: 'evaluation@example.invalid',
      password: 'Controlled1!Pass',
      fullName: 'Evaluation User',
      orgName: 'Evaluation Org',
      controlledEvaluationAccepted: true,
      accessCode: 'operator-code',
    });

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/auth/register',
      expect.objectContaining({ method: 'POST' }),
    );
    const request = fetchMock.mock.calls[0][1] as RequestInit;
    expect(JSON.parse(request.body as string)).toEqual({
      email: 'evaluation@example.invalid',
      password: 'Controlled1!Pass',
      full_name: 'Evaluation User',
      org_name: 'Evaluation Org',
      controlled_evaluation_accepted: true,
      access_code: 'operator-code',
    });
  });
});
