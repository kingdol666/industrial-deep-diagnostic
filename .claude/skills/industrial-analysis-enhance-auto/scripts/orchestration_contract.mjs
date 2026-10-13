import crypto from 'node:crypto';
import fs from 'node:fs';

export function reviewStatus(review) {
  if (!review || !['pass', 'warn', 'fail'].includes(review.verdict)) return 'fail';
  if (!Number.isFinite(review.overall_score) || review.overall_score < 0 || review.overall_score > 100) return 'fail';
  if (!Array.isArray(review.blocking_issues) || review.blocking_issues.length > 0) return 'fail';
  if (review.verdict === 'fail') return 'fail';
  if (review.verdict === 'warn') return 'warn';
  return 'pass';
}

export function reviewIsPassing(review) {
  return reviewStatus(review) === 'pass';
}

export function resolveEnhancementStatus({ launchOk, knowledgeStatus, review }) {
  if (!launchOk || !['READY', 'READY_WITH_WARNINGS'].includes(knowledgeStatus)) return 'FAILED';
  const verdict = reviewStatus(review);
  if (verdict !== 'pass') return 'FAILED';
  return knowledgeStatus;
}

export function shouldBuildAssociationGraph({ e3Ok, graphExists }) {
  if (!e3Ok) return false;
  return !graphExists;
}

export function isFreshBySignature(previous, current) {
  if (!previous || !current || previous.scriptHash !== current.scriptHash) return false;
  const prior = previous.inputs || {};
  const now = current.inputs || {};
  const priorKeys = Object.keys(prior).sort();
  const currentKeys = Object.keys(now).sort();
  if (priorKeys.length !== currentKeys.length || priorKeys.some((k, i) => k !== currentKeys[i])) return false;
  return priorKeys.every((key) => prior[key] === now[key]);
}

export function fileHash(filePath) {
  if (!filePath || !fs.existsSync(filePath)) return null;
  const stat = fs.statSync(filePath);
  if (!stat.isFile()) return null;
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}
