const assert = require('node:assert/strict');
const test = require('node:test');

const Anthropic = require('@anthropic-ai/sdk').default;
const OpenAI = require('openai').default;
const { wrapAnthropic, wrapOpenAI } = require('../dist/wrap');

const DEPLOYMENT_BASE_URL = 'https://guard.example.test';
const AGENTGUARD_KEY = 'ag_test_key';
const PROVIDER_KEY = 'provider-secret-must-not-leave-client';

function requestDetails(input, init) {
  const request = input instanceof Request ? input : new Request(input, init);
  return {
    headers: request.headers,
    url: request.url,
  };
}

test('wrapOpenAI sends auth and metadata through the tracked route', async () => {
  const requests = [];
  const client = new OpenAI({
    apiKey: PROVIDER_KEY,
    maxRetries: 0,
    fetch: async (input, init) => {
      requests.push(requestDetails(input, init));
      return new Response(
        JSON.stringify({
          id: 'chatcmpl-test',
          object: 'chat.completion',
          created: 0,
          model: 'gpt-4o-mini',
          choices: [
            {
              index: 0,
              message: { role: 'assistant', content: 'ok' },
              finish_reason: 'stop',
            },
          ],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    },
  });

  const wrapped = wrapOpenAI(client, {
    apiKey: AGENTGUARD_KEY,
    baseUrl: DEPLOYMENT_BASE_URL,
    endpointId: 'endpoint-id',
    metadata: { session: 'session-id' },
  });
  await wrapped.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [{ role: 'user', content: 'hello' }],
  });

  assert.notEqual(wrapped, client);
  assert.equal(
    requests[0].url,
    `${DEPLOYMENT_BASE_URL}/api/v1/proxy/v1/chat/completions`,
  );
  assert.equal(requests[0].headers.get('Authorization'), `Bearer ${AGENTGUARD_KEY}`);
  assert.equal(requests[0].headers.get('X-AgentGuard-Endpoint-Id'), 'endpoint-id');
  assert.equal(requests[0].headers.get('X-AgentGuard-session'), 'session-id');
  assert.equal([...requests[0].headers.values()].includes(PROVIDER_KEY), false);
});

test('wrapAnthropic sends bearer auth through the tracked messages route', async () => {
  const requests = [];
  const client = new Anthropic({
    apiKey: PROVIDER_KEY,
    maxRetries: 0,
    fetch: async (input, init) => {
      requests.push(requestDetails(input, init));
      return new Response(
        JSON.stringify({
          id: 'msg_test',
          type: 'message',
          role: 'assistant',
          model: 'claude-sonnet-4-20250514',
          content: [{ type: 'text', text: 'ok' }],
          stop_reason: 'end_turn',
          stop_sequence: null,
          usage: { input_tokens: 1, output_tokens: 1 },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    },
  });

  const wrapped = wrapAnthropic(client, {
    apiKey: AGENTGUARD_KEY,
    baseUrl: `${DEPLOYMENT_BASE_URL}/`,
    endpointId: 'endpoint-id',
    metadata: { session: 'session-id' },
  });
  await wrapped.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 1,
    messages: [{ role: 'user', content: 'hello' }],
  });

  assert.notEqual(wrapped, client);
  assert.equal(
    requests[0].url,
    `${DEPLOYMENT_BASE_URL}/api/v1/proxy/v1/messages`,
  );
  assert.equal(requests[0].headers.get('Authorization'), `Bearer ${AGENTGUARD_KEY}`);
  assert.equal(requests[0].headers.get('x-api-key'), AGENTGUARD_KEY);
  assert.equal(requests[0].headers.get('X-AgentGuard-Endpoint-Id'), 'endpoint-id');
  assert.equal(requests[0].headers.get('X-AgentGuard-session'), 'session-id');
  assert.equal([...requests[0].headers.values()].includes(PROVIDER_KEY), false);
});

test('wrappers reject lookalike clients that cannot apply transport options', () => {
  assert.throws(
    () => wrapOpenAI({}, { apiKey: AGENTGUARD_KEY, baseUrl: DEPLOYMENT_BASE_URL }),
    /withOptions/,
  );
});

test('wrappers reject a non-origin deployment URL before attaching credentials', () => {
  const client = new OpenAI({ apiKey: PROVIDER_KEY });
  assert.throws(
    () => wrapOpenAI(client, {
      apiKey: AGENTGUARD_KEY,
      baseUrl: 'https://guard.example.test/untrusted-path',
    }),
    /deployment origin/,
  );
});
