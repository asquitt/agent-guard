'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const { normalizeBaseUrl } = require('../dist/base-url');
const {
  AgentGuardCallbackHandler,
  AgentGuardClient,
  AgentGuardCrewAIHandler,
  AgentGuardLangGraphHandler,
} = require('../dist');

test('deployment base URL must be an absolute HTTP(S) URL', () => {
  for (const value of [
    '',
    'localhost:8001',
    '/relative',
    'ftp://guard.example.test',
    'http://guard.example.test',
    'http://192.168.1.10:8001',
    'http://10.0.0.5:8001',
    'https://user:password@guard.example.test',
    'https://guard.example.test/api/v1',
    'https://guard.example.test?target=other',
    'https://guard.example.test/#fragment',
  ]) {
    assert.throws(() => normalizeBaseUrl(value), TypeError);
  }
  assert.equal(
    normalizeBaseUrl('https://guard.example.test///'),
    'https://guard.example.test',
  );
  assert.equal(normalizeBaseUrl('http://localhost:8001/'), 'http://localhost:8001');
  assert.equal(normalizeBaseUrl('http://127.0.0.1:8001'), 'http://127.0.0.1:8001');
  assert.equal(normalizeBaseUrl('http://[::1]:8001'), 'http://[::1]:8001');
});

test('every credential-bearing client requires an explicit deployment base URL', () => {
  for (const Client of [
    AgentGuardClient,
    AgentGuardCallbackHandler,
    AgentGuardCrewAIHandler,
    AgentGuardLangGraphHandler,
  ]) {
    assert.throws(() => new Client({ apiKey: 'ag_test_key' }), TypeError);
  }
});

function capturedRequest(input, init) {
  return input instanceof Request ? input : new Request(input, init);
}

test('low-level client sends proxy and management credentials to their exact routes', async () => {
  const originalFetch = global.fetch;
  const requests = [];
  global.fetch = async (input, init) => {
    const request = capturedRequest(input, init);
    requests.push(request);
    if (request.url.includes('/incidents/')) {
      return new Response(JSON.stringify({ items: [], total: 0 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    return new Response(JSON.stringify({ choices: [] }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  try {
    const client = new AgentGuardClient({
      apiKey: 'ag_test_key',
      accessToken: 'user-access-token',
      baseUrl: 'https://guard.example.test/',
      maxRetries: 1,
    });
    await client.proxy('/v1/chat/completions', {
      model: 'gpt-4o-mini',
      messages: [],
    });
    await client.listIncidents();

    assert.equal(
      requests[0].url,
      'https://guard.example.test/api/v1/proxy/v1/chat/completions',
    );
    assert.equal(requests[0].headers.get('Authorization'), 'Bearer ag_test_key');
    assert.equal(
      requests[1].url,
      'https://guard.example.test/api/v1/incidents/',
    );
    assert.equal(
      requests[1].headers.get('Authorization'),
      'Bearer user-access-token',
    );
  } finally {
    global.fetch = originalFetch;
  }
});

test('management methods fail closed without a user access token', async () => {
  const client = new AgentGuardClient({
    apiKey: 'ag_test_key',
    baseUrl: 'https://guard.example.test',
  });
  await assert.rejects(() => client.listIncidents(), /accessToken/);
});

test('event integrations send API-key auth only to the tracked ingest route', async () => {
  const originalFetch = global.fetch;
  const requests = [];
  global.fetch = async (input, init) => {
    requests.push(capturedRequest(input, init));
    return new Response(JSON.stringify({ accepted: 1, message: 'ok' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  try {
    const options = {
      apiKey: 'ag_test_key',
      baseUrl: 'https://guard.example.test/',
    };
    const langchain = new AgentGuardCallbackHandler(options);
    langchain.handleLLMStart({}, ['prompt'], 'run-langchain');
    await langchain.manualFlush();

    const langgraph = new AgentGuardLangGraphHandler(options);
    langgraph.handleLLMStart({}, ['prompt'], 'run-langgraph');
    await langgraph.manualFlush();

    const crewai = new AgentGuardCrewAIHandler(options);
    crewai.onTaskStart('task', 'role');
    await crewai.manualFlush();

    assert.equal(requests.length, 3);
    for (const request of requests) {
      assert.equal(
        request.url,
        'https://guard.example.test/api/v1/ingest/events',
      );
      assert.equal(request.headers.get('Authorization'), 'Bearer ag_test_key');
    }
  } finally {
    global.fetch = originalFetch;
  }
});
