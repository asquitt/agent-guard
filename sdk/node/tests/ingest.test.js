'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
  AgentGuardCallbackHandler,
  AgentGuardCrewAIHandler,
  AgentGuardLangGraphHandler,
} = require('../dist');

const OPTIONS = {
  apiKey: 'ag_test_key',
  baseUrl: 'https://guard.example.test',
};

test('manual flush raises on HTTP failure and retries the retained batch', async () => {
  const originalFetch = global.fetch;
  const requests = [];
  let responseStatus = 500;
  global.fetch = async (input, init) => {
    requests.push(input instanceof Request ? input : new Request(input, init));
    return new Response(
      JSON.stringify(responseStatus < 400 ? { accepted: 1 } : { detail: 'failed' }),
      {
        status: responseStatus,
        headers: { 'Content-Type': 'application/json' },
      },
    );
  };

  const cases = [
    {
      status: 401,
      handler: new AgentGuardCallbackHandler(OPTIONS),
      emit: (handler) => handler.handleLLMStart({}, ['prompt'], 'langchain-run'),
    },
    {
      status: 500,
      handler: new AgentGuardLangGraphHandler(OPTIONS),
      emit: (handler) => handler.handleLLMStart({}, ['prompt'], 'langgraph-run'),
    },
    {
      status: 500,
      handler: new AgentGuardCrewAIHandler(OPTIONS),
      emit: (handler) => handler.onTaskStart('task', 'role'),
    },
  ];

  try {
    for (const item of cases) {
      item.emit(item.handler);
      responseStatus = item.status;
      const failedRequestIndex = requests.length;
      await assert.rejects(
        () => item.handler.manualFlush(),
        new RegExp(`HTTP ${item.status}`),
      );

      responseStatus = 200;
      await item.handler.manualFlush();

      const failed = requests[failedRequestIndex];
      const retried = requests[failedRequestIndex + 1];
      assert.equal(failed.url, 'https://guard.example.test/api/v1/ingest/events');
      assert.equal(retried.url, failed.url);
      assert.equal(await retried.clone().text(), await failed.clone().text());
    }
  } finally {
    global.fetch = originalFetch;
  }
});
