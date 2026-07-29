#!/usr/bin/env node
// log-agent-event.mjs — Auto-log agent_start/agent_complete events
// Called automatically by sub-agents at start/end
// Usage: node log-agent-event.mjs <run_dir> <agent_name> start|complete [--files file1,file2]

import fs from 'fs';
import { join } from 'path';

const args = process.argv.slice(2);
const runDir = args[0];
const agentName = args[1];
const action = args[2]; // 'start' or 'complete'

if (!runDir || !agentName || !['start', 'complete'].includes(action)) {
  console.error('Usage: node log-agent-event.mjs <run_dir> <agent_name> start|complete [--files f1,f2]');
  process.exit(1);
}

const filesIdx = args.indexOf('--files');
const files = filesIdx >= 0 ? args[filesIdx + 1]?.split(',') : [];

const logPath = join(runDir, '.pipeline_events.jsonl');
const event = {
  event: action === 'start' ? 'agent_start' : 'agent_complete',
  agent: agentName,
  timestamp: new Date().toISOString(),
  step: agentName.replace(/-/g, '_')
};
if (action === 'complete' && files.length > 0) {
  event.files_written = files;
}

fs.appendFileSync(logPath, JSON.stringify(event) + '\n');
console.log(JSON.stringify({ ok: true, event: event.event, agent: agentName }));
