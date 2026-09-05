'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
  AgentGuardError,
  DetectionBlockedError,
  raiseForStatus,
} = require('../dist/errors');

test('tracked detection block shape maps to DetectionBlockedError', () => {
  assert.throws(
    () => raiseForStatus(403, JSON.stringify({
      error: {
        type: 'detection_blocked',
        message: 'Request blocked by security policy',
      },
    })),
    DetectionBlockedError,
  );
});

test('unrelated forbidden response is not mislabeled as detector enforcement', () => {
  assert.throws(
    () => raiseForStatus(403, JSON.stringify({ detail: 'IP not allowed' })),
    (error) => error instanceof AgentGuardError
      && !(error instanceof DetectionBlockedError)
      && error.statusCode === 403,
  );
});
