// Run Queue — FIFO admission queue for diagnosis executions (P0-5 concurrency).
//
// The service caps how many runs may execute at once (env MAX_CONCURRENT_RUNS →
// config diagnosis.max_concurrent_runs). A run that would exceed the cap is
// admitted here instead of starting; when an executing run reaches a terminal
// state the service dequeues the next waiting run and starts it through the
// exact same execution path as a direct start (see drainExecutionQueue in
// diagnosis.service.mjs).
//
// Deliberately dependency-free and fully synchronous: admission order must be
// exactly call order, and every accessor must be side-effect free so the
// capacity check cannot race with the drain that follows it.

export function createRunQueue() {
  /** @type {string[]} oldest-first */
  let items = [];

  return {
    /**
     * Append a run id. A run id already waiting keeps its position (a repeated
     * /execute must not consume a second slot) — returns the 1-based position.
     */
    enqueue(runId) {
      if (!runId) return 0;
      const existing = items.indexOf(runId);
      if (existing !== -1) return existing + 1;
      items.push(runId);
      return items.length;
    },

    /** Take the oldest waiting run id, or null when the queue is empty. */
    dequeue() {
      return items.length > 0 ? items.shift() : null;
    },

    /** Drop a run id (stopped while waiting). Returns true when it was waiting. */
    remove(runId) {
      const index = items.indexOf(runId);
      if (index === -1) return false;
      items.splice(index, 1);
      return true;
    },

    has(runId) {
      return items.includes(runId);
    },

    /** 1-based position of a waiting run, 0 when it is not waiting. */
    positionOf(runId) {
      const index = items.indexOf(runId);
      return index === -1 ? 0 : index + 1;
    },

    /** Snapshot of waiting run ids, oldest first. */
    list() {
      return [...items];
    },

    clear() {
      items = [];
    },

    get size() {
      return items.length;
    },
  };
}
