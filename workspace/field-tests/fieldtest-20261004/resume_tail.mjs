// Resume driver: spawn `omp --mode=rpc`, send the tail-continuation prompt,
// log every NDJSON event, exit when the terminal agent_end arrives.
import { spawn } from 'child_process';
import { createInterface } from 'readline';
import { mkdirSync, writeFileSync, appendFileSync } from 'fs';
import { join, resolve } from 'path';

const ROOT = resolve(import.meta.dirname, '..', '..', '..');
const RUN_DIR = 'workspace/diagnostic-runs/202610041453153_cement_ball_mill_e2e';
const SESSION_DIR = join(ROOT, 'workspace', '.omp-sessions', 'resume-tail-20261005');
mkdirSync(SESSION_DIR, { recursive: true });
const LOG = join(ROOT, 'workspace', 'field-tests', 'fieldtest-20261004', 'e2e', 'tail_events.jsonl');
writeFileSync(LOG, '');

const PROMPT = `你在续跑一个因主机休眠中断的工业诊断 run。run 目录: ${RUN_DIR}（相对仓库根，先 cd 到仓库根再操作）。

当前状态（读 .pipeline_events.jsonl 确认）:
- Step 0-5 已完成: 数据分析/本体/诊断(diagnosis.json COMPETING_SET)/judge(judge_feedback.json 98分 pass)/物理预审
- Step 5b 修复回路执行过两轮 repair_spawn，optimization_preflight.md 存在，最后事件是 16:53Z 的修复
- 你需要先用仓库的检查点命令核实状态（不要重跑已完成步骤）

你的任务（严格按 .claude/skills/industrial-analysis-auto/SKILL.md 与其 references/agent-protocol.md 执行）:
1. 核实 Step 5a/5b 状态：judge 是否 pass、预审修复是否已落盘；若预审仍有 P1 未修复项，先完成修复
2. 执行 Step 6: 调度 reporter 技能产出 report.md（9 段金字塔中文报告）+ run_summary.json
3. 执行 Step 7: 调度 industrial-physical-auditor(FINAL_AUDIT) 产出 optimizer.md 且必须 ENDORSED
4. 执行 Step 8: 调度 industrial-html-visualizer 产出 diagnostic-report.html（render_manifest 先行）
5. 执行 Step 8.5: 调度 industrial-html-reviewer 产出 html_review.json
6. 执行 Step 9: finalize + evidence_closure_report + 经验蒸馏(experience_distill)
7. 每步完成后向 .pipeline_events.jsonl 追加对应 step_complete 事件，遵守 CP-6~CP-9 检查点

纪律: 不得读取 data/cement_ball_mill/ground_truth.md；数值只能来自 run 目录已有产物；语言为中文报告。完成后输出 "TAIL_COMPLETE"。`;

const proc = spawn('omp', ['--mode=rpc', '-p', '--auto-approve',
  `--session-dir=${SESSION_DIR}`], { cwd: ROOT, shell: false });

const rl = createInterface({ input: proc.stdout });
let ready = false;
const timer = setTimeout(() => {
  appendFileSync(LOG, JSON.stringify({ event: 'driver_timeout_ms', ms: 100 * 60 * 1000 }) + '\n');
  proc.kill();
  process.exit(2);
}, 100 * 60 * 1000);

rl.on('line', (line) => {
  appendFileSync(LOG, line + '\n');
  let msg = null;
  try { msg = JSON.parse(line); } catch { return; }
  if (!ready && msg.type === 'ready') {
    ready = true;
    proc.stdin.write(JSON.stringify({ type: 'prompt', message: PROMPT }) + '\n');
  }
  if (msg.type === 'agent_end' && msg.isTerminal) {
    clearTimeout(timer);
    appendFileSync(LOG, JSON.stringify({ event: 'driver_done' }) + '\n');
    process.exit(0);
  }
});
proc.stderr.on('data', (d) => appendFileSync(LOG, JSON.stringify({ stderr: String(d).slice(0, 500) }) + '\n'));
proc.on('exit', (code) => { clearTimeout(timer); appendFileSync(LOG, JSON.stringify({ event: 'proc_exit', code }) + '\n'); process.exit(code ?? 0); });
