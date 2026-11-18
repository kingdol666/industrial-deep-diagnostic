# Cover Letter — Advanced Engineering Informatics submission

Dear Editor-in-Chief,

We are pleased to submit our manuscript **"Auditable agentic diagnosis for industrial processes: evidence-graded competing-hypothesis reasoning evaluated against per-fault literature baselines"** for consideration in Advanced Engineering Informatics.

Large language models are increasingly proposed for industrial root-cause analysis, but their conclusions typically arrive as free-form text with no evidence structure, no calibrated confidence, and no machine-checkable evaluation. We present the Industrial Deep Diagnostic (IDD) pipeline, which turns LLM-based RCA into an auditable engineering procedure: deterministic statistics feed a competing-hypotheses diagnostician whose verdicts are three-state (determined / capped competing set / needs-data), reported confidence is bounded by the weakest item of graded evidence (L1–L7), and bounded-repair quality gates with a finalization execution proof stand behind every result.

The paper's central contribution is the machine-checked evaluation contract built around this pipeline: truth isolation with data fingerprinting, provenance-labeled stage-authored artifacts, and gate-graded scoring, evaluated on a 12-scenario benchmark spanning SKAB, the Tennessee Eastman Process, and IndPenSim. In keeping with the contract, the paper reports an unfavorable result with the same rigor as the favorable ones: a bare call to the same model scores 9/9 on the keyword instrument where the pipeline resolves 4/9 and caps five verdicts — and we show from the released gradings that the cap is a computed operating point on the risk–coverage curve (forced commitment would yield 6/9 with three wrong root causes). Every number in the paper traces to a released artifact, and the complete evaluation artifact layer accompanies the submission as supplementary material.

The manuscript engages directly with recent work in this journal on LLM-based fault diagnosis (CausalKGPT, FD-LLM, LLM-orchestrated troubleshooting, digital-twin multi-scenario diagnosis), and supplies the element none of these systems provide: cap-enforced three-state conclusions together with a machine-verifiable, end-to-end replayable evaluation harness.

This manuscript is original, has not been published previously, and is not under consideration elsewhere. The author declares no competing interests; no funding was received; the use of AI-assisted tools in preparing the work is declared in the manuscript per Elsevier policy; and a data availability statement is included.

Thank you for your consideration.

Sincerely,
Haozheng Zhang (sole author and corresponding author)
Institute of Advanced Technology, University of Science and Technology of China, Hefei 230088, China
zhanghaozheng@ustc.edu.cn
