// Enhance Intent — 从用户问题中检测"深度诊断"意图（零 LLM 成本的规则引擎）。
//
// 策略三态：
//   'on'    — 用户显式要求深度增强（前端勾选或强信号关键词），基线完成后自动执行 E0-E8
//   'off'   — 用户明确只要普通诊断（或前端关闭）
//   'auto'  — 由本引擎检测：强信号命中 → on；弱信号≥2 → on（软触发）；否则普通流程
//
// 设计原则：误报可接受（增强脚本链便宜且只读基线产物），漏报不可接受（用户要深挖却没给）。

// 强信号：出现即视为明确的深度诊断意图
const STRONG_SIGNALS = [
  '深度诊断', '深度分析', '深度增强', '增强诊断', '增强分析', '深挖', '深入分析',
  '根因机理', '物理机理', '机理验证', '机理分析', '物理验证', '物理桥接',
  '条件分析', '关联分析全量', '反事实', '权衡分析', '可操作建议',
  'deep diagnosis', 'deep analysis', 'deep dive', 'enhanced analysis', 'enhance',
  'physics bridge', 'physics verification', 'mechanism chain', 'association graph',
  'e0-e8', 'full pipeline enhancement',
];

// 弱信号：单一出现不足以触发，≥2 条视为软触发
const WEAK_SIGNALS = [
  '全面', '彻底', '完整分析', '深入', '彻底排查', '所有原因', '每个参数', '关联',
  '为什么', 'how exactly', 'why exactly', 'thorough', 'comprehensive', 'exhaustive',
];

// 显式关闭信号：用户明确表示只要快速/简单结果
const OFF_SIGNALS = [
  '只要快速', '快速诊断即可', '简单诊断', '无需深入', '不用深入', '简单看看',
  'quick check only', 'simple diagnosis only', 'no deep analysis', "don't dig deeper",
];

export function detectEnhanceIntent(userQuestion) {
  const text = String(userQuestion || '').toLowerCase();
  const matchedStrong = STRONG_SIGNALS.filter(k => text.includes(k.toLowerCase()));
  const matchedWeak = WEAK_SIGNALS.filter(k => text.includes(k.toLowerCase()));
  const matchedOff = OFF_SIGNALS.filter(k => text.includes(k.toLowerCase()));

  // 显式关闭信号优先（用户明确不要深度）
  if (matchedOff.length > 0) {
    return { intentHit: false, confidence: 'explicit_off', matched: matchedOff, policy: 'off' };
  }
  if (matchedStrong.length > 0) {
    return { intentHit: true, confidence: 'strong', matched: matchedStrong, policy: 'on' };
  }
  if (matchedWeak.length >= 2) {
    return { intentHit: true, confidence: 'weak_x' + matchedWeak.length, matched: matchedWeak, policy: 'on' };
  }
  return { intentHit: false, confidence: matchedWeak.length === 1 ? 'weak_x1' : 'none', matched: matchedWeak, policy: 'none' };
}

/**
 * 解析运行级增强策略。
 * @param {string|undefined} requested  用户显式选择：'auto' | 'on' | 'off'（undefined → 'auto'）
 * @param {string|undefined} userQuestion
 * @returns {{policy: 'auto'|'on'|'off', intentHit: boolean, confidence: string, matched: string[]}}
 */
export function resolveEnhancementPolicy(requested, userQuestion) {
  const normalized = typeof requested === 'string' ? requested.trim().toLowerCase() : 'auto';
  const detection = detectEnhanceIntent(userQuestion);

  if (normalized === 'on') return { policy: 'on', intentHit: true, confidence: 'user_forced', matched: [] };
  if (normalized === 'off') return { policy: 'off', intentHit: false, confidence: 'user_off', matched: [] };
  // auto：检测结果决定 policy（on），否则保持 auto 由管线内二次判断/提示
  if (detection.policy === 'off') return { policy: 'off', intentHit: false, confidence: detection.confidence, matched: detection.matched };
  if (detection.intentHit) return { policy: 'on', intentHit: true, confidence: detection.confidence, matched: detection.matched };
  return { policy: 'auto', intentHit: false, confidence: detection.confidence, matched: detection.matched };
}
