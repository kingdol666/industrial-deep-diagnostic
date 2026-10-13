import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = readFileSync(path.join(repo, 'scripts/test-skills.mjs'), 'utf8');

test('skill static gate accepts Chinese descriptions and skill body text', () => {
  assert.match(source, /description is non-empty and includes "Trigger:" keywords \(language follows repo policy\)/);
  assert.match(source, /body may use the repository's configured output language/);
  assert.doesNotMatch(source, /check\(skill, 'G5', cjkMatches\.length === 0/);
});
