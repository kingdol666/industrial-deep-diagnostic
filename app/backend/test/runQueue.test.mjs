// Run queue — FIFO admission for diagnosis executions beyond MAX_CONCURRENT_RUNS.
// Pure module on purpose: the service's capacity check and its FIFO drain read
// this state synchronously, so order / dedup / positions must be exactly call
// order with no hidden asynchrony.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

const { createRunQueue } = await import('../src/services/runQueue.mjs');

describe('createRunQueue — FIFO admission', () => {
  test('dequeues in FIFO order regardless of enqueue bookkeeping', () => {
    const q = createRunQueue();
    assert.equal(q.size, 0);
    assert.equal(q.dequeue(), null);
    assert.equal(q.enqueue('run-a'), 1);
    assert.equal(q.enqueue('run-b'), 2);
    assert.equal(q.enqueue('run-c'), 3);
    assert.equal(q.size, 3);
    assert.deepEqual(q.list(), ['run-a', 'run-b', 'run-c']);
    assert.equal(q.dequeue(), 'run-a');
    assert.equal(q.dequeue(), 'run-b');
    assert.equal(q.dequeue(), 'run-c');
    assert.equal(q.dequeue(), null);
    assert.equal(q.size, 0);
  });

  test('enqueue is idempotent per run id and keeps the original position', () => {
    const q = createRunQueue();
    q.enqueue('run-a');
    q.enqueue('run-b');
    // A repeated /execute for a waiting run must neither duplicate the entry
    // nor move it to the back of the queue.
    assert.equal(q.enqueue('run-a'), 1);
    assert.deepEqual(q.list(), ['run-a', 'run-b']);
    assert.equal(q.enqueue(''), 0);
    assert.equal(q.size, 2);
  });

  test('positionOf / has / remove operate on waiting ids only', () => {
    const q = createRunQueue();
    q.enqueue('run-a');
    q.enqueue('run-b');
    assert.equal(q.positionOf('run-a'), 1);
    assert.equal(q.positionOf('run-b'), 2);
    assert.equal(q.positionOf('run-z'), 0);
    assert.equal(q.has('run-b'), true);
    assert.equal(q.remove('run-a'), true);
    assert.equal(q.remove('run-a'), false);
    assert.deepEqual(q.list(), ['run-b']);
    assert.equal(q.positionOf('run-b'), 1);
    assert.equal(q.size, 1);
    q.clear();
    assert.equal(q.size, 0);
    assert.equal(q.has('run-b'), false);
  });
});
