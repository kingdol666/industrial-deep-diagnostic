// engine-options.mjs — per-harness MODEL + PERMISSION-MODE catalogs.
//
// 设计原则（与引擎真实设计一致）：
//   - 每个引擎只暴露它真实支持的选项；不支持的维度返回空数组（前端隐藏该下拉）。
//   - 模型目录来源：
//       claude → config.claude.model（默认）+ Claude Code 内建别名（sonnet/opus/haiku）
//       codex  → ~/.codex/config.toml 的 model + model_catalog_json 模型目录（用户真实配置）
//       一次性/驻留 CLI → config.harness.engines.<id>.model（配置了才暴露）
//       omp / mock → 无模型切换维度（空）
//   - 权限模式来源 = 引擎自身的审批设计：
//       claude → SDK permissionMode（default/acceptEdits/plan/bypassPermissions）
//       omp → --auto-approve 常驻设计（单一模式）
//       codex → app-server approvalPolicy（on-request/on-failure/never/untrusted）
//       一次性 + ACP 家族 → 客户端自动放行（单一模式）
//       mock → 剧本（单一模式）

import { readFileSync, existsSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';
import { config } from '../../../../config/loader.mjs';

const CODEX_HOME = process.env.CODEX_HOME || join(homedir(), '.codex');

function readCodexModelCatalog() {
  // Returns { defaultModel, models: [{ id, label }] } from the user's codex
  // config: `model` is the configured default; `model_catalog_json` (when
  // present) is the configured catalog of switchable models.
  try {
    const cfgPath = join(CODEX_HOME, 'config.toml');
    if (!existsSync(cfgPath)) return { defaultModel: null, models: [] };
    const text = readFileSync(cfgPath, 'utf-8');
    const model = (text.match(/^model\s*=\s*"([^"]+)"/m) || [])[1] || null;
    const catalogRel = (text.match(/^model_catalog_json\s*=\s*"([^"]+)"/m) || [])[1] || null;
    const models = [];
    if (catalogRel) {
      const catPath = join(CODEX_HOME, catalogRel);
      if (existsSync(catPath)) {
        const cat = JSON.parse(readFileSync(catPath, 'utf-8'));
        for (const m of cat.models || []) {
          const id = m.id || m.slug;
          if (id) models.push({ id, label: m.display_name || m.label || id });
        }
      }
    }
    // config 的 model 一定在目录首位（它是 codex 实际加载的默认模型）
    if (model && !models.some((m) => m.id === model)) models.unshift({ id: model, label: model });
    return { defaultModel: model, models };
  } catch {
    return { defaultModel: null, models: [] };
  }
}

const CLAUDE_MODEL_ALIASES = [
  { id: 'sonnet', label: 'sonnet（快速）' },
  { id: 'opus', label: 'opus（深度）' },
  { id: 'haiku', label: 'haiku（轻量）' },
];

export function getEngineOptions(id) {
  switch (id) {
    case 'claude': {
      const def = config.claude?.model || 'claude-opus-4-7';
      const models = [{ id: def, label: `${def}（默认）`, default: true }];
      for (const a of CLAUDE_MODEL_ALIASES) {
        if (a.id !== def) models.push({ ...a });
      }
      return {
        models,
        permissionModes: [
          { id: 'bypassPermissions', label: 'Bypass permissions（全自动，管线默认）', default: true },
          { id: 'acceptEdits', label: 'Accept edits（自动接受文件编辑）' },
          { id: 'plan', label: 'Plan（只读规划）' },
          { id: 'default', label: 'Default（逐次询问）' },
        ],
      };
    }
    case 'codex': {
      const { defaultModel, models } = readCodexModelCatalog();
      const modelList = (models.length ? models : (defaultModel ? [{ id: defaultModel, label: defaultModel }] : []))
        .map((m) => ({ ...m, default: m.id === defaultModel }));
      return {
        models: modelList,
        permissionModes: [
          { id: 'on-request', label: 'on-request（按需请求审批，默认）', default: true },
          { id: 'on-failure', label: 'on-failure（失败时请求审批）' },
          { id: 'never', label: 'never（从不请求审批）' },
          { id: 'untrusted', label: 'untrusted（最小信任）' },
        ],
      };
    }
    case 'omp':
      return {
        models: [],
        permissionModes: [{ id: 'auto-approve', label: 'auto-approve（--auto-approve 常驻设计）', default: true }],
      };
    case 'mock':
      return {
        models: [],
        permissionModes: [{ id: 'scripted', label: 'scripted（进程内剧本）', default: true }],
      };
    default: {
      // 一次性家族（gemini/copilot/cursor/goose/pi）与 ACP 家族（dsh/hermes/qwen）、
      // opencode、crush：模型槽位来自 config.harness.engines.<id>.model（配置了才暴露）；
      // 权限为客户端自动放行的单一设计。
      const cfgModel = config.harness?.engines?.[id]?.model || null;
      return {
        models: cfgModel ? [{ id: cfgModel, label: `${cfgModel}（默认）`, default: true }] : [],
        permissionModes: [{ id: 'auto-approve', label: 'auto-approve（客户端自动放行）', default: true }],
      };
    }
  }
}

/** Validate a requested model / permissionMode against the engine catalog. */
export function validateEngineOption(id, { model, permissionMode } = {}) {
  const opts = getEngineOptions(id);
  const errors = [];
  if (model && !opts.models.some((m) => m.id === model)) {
    errors.push({
      code: 'MODEL_NOT_SUPPORTED',
      message: `harness "${id}" has no configured model "${model}" — available: ${opts.models.map((m) => m.id).join(', ') || '(none)'}`,
    });
  }
  if (permissionMode && !opts.permissionModes.some((m) => m.id === permissionMode)) {
    errors.push({
      code: 'PERMISSION_NOT_SUPPORTED',
      message: `harness "${id}" does not support permission mode "${permissionMode}" — available: ${opts.permissionModes.map((m) => m.id).join(', ') || '(none)'}`,
    });
  }
  return { ok: errors.length === 0, errors, options: opts };
}
