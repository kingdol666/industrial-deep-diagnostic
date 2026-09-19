# 物理预审计（Step 5b, pre-report）
run: solo_tep_d07  time: 2026-09-17T16:49:24.959675+00:00
auditor: report-reviewer (industrial-physical-auditor protocol, inline)

## 机制链物理核查
1. 阀门开大+流量恢复 ⇒ 上游供给压力损失（阀门口径关系）：【通过】
2. 三段结构（XMEAS_4 瞬跌 -12.29σ / XMV_4 +18.73σ→+12.24σ 保持 / 流量恢复）：【通过】
3. 反应器压力瞬态后重控 0.01σ：受控后果而非根源。【通过】
4. 其它进料阀 held ≤0.25σ：扰动局限于流股4。【通过】

## 数据真相抽查
- XMV_4 +25.13%、XMEAS_4 dip -12.29σ 可由 segment_statistics 与瞬态分析复算。【通过】
- timestamp 轴解析合法。【通过】

## 发现
- 无 FATAL 发现。

## 结论
预审计通过（0 FATAL），可进入报告阶段。
