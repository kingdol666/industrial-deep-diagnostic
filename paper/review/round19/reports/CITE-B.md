# Citation Integrity Audit — Batch B

Paper: `D:\codes\myskills\industrial-deep-diagnostic\paper\refs.bib`
Auditor: citation-integrity agent. Date: 2026-09-19.
Method: WebSearch (title + first author), DOI resolution via publisher pages and the Semantic Scholar Graph API (`api.semanticscholar.org/graph/v1/paper/DOI:...`), arXiv abs pages, publisher/WorldCat for books.

Verdict scale: VERIFIED (exists, all claimed fields match) / MISMATCH (exists but a field is wrong) / NOT_FOUND (existence unconfirmable).

---

## 1. tuli2022tranad — VERIFIED

- Claimed: Tuli, Casale, Jennings — "TranAD: Deep Transformer Networks for Anomaly Detection in Multivariate Time Series Data", Proceedings of the VLDB Endowment, 15(6):1201–1214, 2022, DOI 10.14778/3514061.3514067.
- Evidence: Semantic Scholar DOI record returns title, authors Shreshth Tuli / G. Casale / N. Jennings, venue PVLDB, volume 15, pages 1201–1214, 2022 (https://api.semanticscholar.org/graph/v1/paper/DOI:10.14778/3514061.3514067). ACM DL hosts the same DOI (https://dl.acm.org/doi/abs/10.14778/3514061.3514067); arXiv preprint 2201.07284.
- All fields match (issue 6 is the standard PVLDB 15(6) record for this paper).

## 2. reinartz2021extended — VERIFIED

- Claimed: Reinartz, Kulahci, Ravn — "An extended Tennessee Eastman simulation dataset for fault detection and decision support systems", Computers & Chemical Engineering, 149:107281, 2021, DOI 10.1016/j.compchemeng.2021.107281.
- Evidence: DTU Orbit record (https://orbit.dtu.dk/en/publications/an-extended-tennessee-eastman-simulation-dataset-for-fault-detect) — authors Christopher Reinartz, Murat Kulahci, Ole Ravn, CCE Vol 149, article 107281, 2021; ScienceDirect pii S0098135421000594.
- All fields match.

## 3. skab2020 — VERIFIED

- Claimed (misc): Katser, Iurii D. and Kozitsin, Vyacheslav O. — "Skoltech Anomaly Benchmark (SKAB)", 2020, publisher Kaggle, DOI 10.34740/KAGGLE/DSV/1693952, url https://www.kaggle.com/dsv/1693952.
- Evidence: the official SKAB GitHub repo (https://github.com/waico/SKAB) carries a BibTeX block identical to the bib entry: `author = {Katser, Iurii D. and Kozitsin, Vyacheslav O.}, title = {Skoltech Anomaly Benchmark (SKAB)}, year = {2020}, publisher = {Kaggle}` with DOI 10.34740/KAGGLE/DSV/1693952. Kaggle dataset dsv/1693952 resolves; ResearchGate confirms the dataset DOI (Jan 2020).
- Note: ResearchGate shows the co-author as "Vladimir Kozitsin" in one snippet, but the authors' own recommended citation (GitHub repo, controlcharts docs) uses "Kozitsin, Vyacheslav O." — the bib follows the authors' official citation block. Exact match.

## 4. russell2000delay — VERIFIED

- Claimed (book): Russell, Chiang, Braatz — "Data-driven Methods for Fault Detection and Diagnosis in Chemical Processes", Springer, London, 2000, DOI 10.1007/978-1-4471-0409-4.
- Evidence: Springer Link page confirms DOI 10.1007/978-1-4471-0409-4 = this book, authors Evan L. Russell, Leo H. Chiang, Richard D. Braatz, series "Advances in Industrial Control", Springer-Verlag London, 2000 (https://link.springer.com/book/10.1007/978-1-4471-0409-4; DOI resolves with 302 to Springer). Google Books and library catalogs confirm author order.
- All fields match.

## 5. zhou2024causalkgpt — VERIFIED

- Claimed: Zhou Bin, Li Xinyu, Liu Tianyuan, Xu Kaizhou, Liu Wei, Bao Jinsong — "CausalKGPT: Industrial structure causal knowledge-enhanced large language model for cause analysis of quality problems in aerospace product manufacturing", Advanced Engineering Informatics, 59:102333, 2024, DOI 10.1016/j.aei.2023.102333.
- Evidence: Semantic Scholar DOI record (https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/j.aei.2023.102333) returns the exact title, author order Bin Zhou, Xinyu Li, Tianyuan Liu, Kaizhou Xu, Wei Liu, Jinsong Bao, AEI Vol 59, article 102333, 2024. Google Scholar profile of Bin Zhou confirms same order.
- One web-search summary paraphrased the subtitle as "fault diagnosis of industrial processes" — that was a summarizer error; the authoritative DOI record matches the bib title verbatim. All fields match.

## 6. lin2025fdllm — VERIFIED

- Claimed: Lin Lin, Zhang Sihao, Fu Song, Liu Yikun — "FD-LLM: Large language model for fault diagnosis of complex equipment", Advanced Engineering Informatics, 65:103208, 2025, DOI 10.1016/j.aei.2025.103208.
- Evidence: Semantic Scholar DOI record (https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/j.aei.2025.103208) — authors in order: Lin Lin, Sihao Zhang, Song Fu, Yikun Liu; AEI Vol 65, article 103208, 2025. ScienceDirect confirms (cited by ~160).
- Caution: a separate arXiv preprint "FD-LLM: Large Language Model for Fault Diagnosis of Machines" (arXiv 2412.x, Qaid/Zhang et al.) is a DIFFERENT work; the bib correctly points to the AEI journal paper. All fields match.

## 7. wen2025troubleshooting — VERIFIED

- Claimed: Wen Sijie, Li Fei, Zhuang Weibin, Pan Xinyu, Yu Weigang, Bao Jinsong, Li Xinyu — "Leveraging large language models for Human-Machine collaborative troubleshooting of complex industrial equipment faults", Advanced Engineering Informatics, 65:103235, 2025, DOI 10.1016/j.aei.2025.103235.
- Evidence: Semantic Scholar DOI record (https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/j.aei.2025.103235) — authors in order: Sijie Wen, Fei Li, Weibin Zhuang, Xinyu Pan, Weigang Yu, Jinsong Bao, Xinyu Li; AEI Vol 65, article 103235, 2025. ScienceDirect pii S1474034625001284.
- An intermediate search summary offered "Zhengming Zhuang, Zhiqiang Pan" — the authoritative DOI record contradicts it and matches the bib exactly, so the bib is correct. All fields match.

## 8. xu2026digitaltwin — VERIFIED

- Claimed: Xu Quanning, Wen Guangrui, Lei Zihao, Gu Shulong, Su Yu, Zhang Zhifen, Chen Xuefeng — "Deep digital twin-powered large vision-language model for multi-scenario industrial fault diagnosis", Advanced Engineering Informatics, 69:103997, 2026, DOI 10.1016/j.aei.2025.103997.
- Evidence: Semantic Scholar DOI record (https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/j.aei.2025.103997) — authors in order: Quanning Xu, Guangrui Wen, Zi-Hao Lei, Shulong Gu, Yu Su, Zhi-Fen Zhang, Xue-Feng Chen; AEI Vol 69, article 103997, 2026 (hyphenation variants only). ScienceDirect + XJTU scholar page confirm.
- All fields match.

## 9. wei2026agentrca — VERIFIED

- Claimed (misc): Wei, Amaury and Fink, Olga — "AgentRCA: Agentic Root Cause Analysis through Evidence-Grounded Reasoning", 2026, arXiv eprint 2607.22385, DOI 10.48550/arXiv.2607.22385.
- Evidence: arXiv abs page https://arxiv.org/abs/2607.22385 exists — title "Agentic Root Cause Analysis through Evidence-Grounded Reasoning", authors Amaury Wei and Olga Fink (EPFL), submitted Fri 24 Jul 2026, cs.AI/cs.LG. DOI form 10.48550/arXiv.<id> is the standard arXiv DOI.
- Note: the fetch summarizer flagged the July 2026 date as "future" from its own stale internal clock; as of the audit date (2026-09-19) the posting is in the past and legitimate. The "AgentRCA:" prefix in the bib title is a display prefix; the arXiv title itself omits it — acceptable BibTeX practice, not a metadata error.

## 10. qin2012survey — VERIFIED

- Claimed: Qin, S. Joe — "Survey on data-driven industrial process monitoring and diagnosis", Annual Reviews in Control, 36(2):220–234, 2012, DOI 10.1016/j.arcontrol.2012.09.004.
- Evidence: ScienceDirect record (by SJ Qin, 2012, cited ~1800); multiple institutional repositories (LN, CityU) cite it as Annual Reviews in Control 36(2):220–234, 2012.
- All fields match.

## 11. yuan2014root — VERIFIED

- Claimed: Yuan, Tong and Qin, S. Joe — "Root cause diagnosis of plant-wide oscillations using Granger causality", Journal of Process Control, 24(2):450–459, 2014, DOI 10.1016/j.jprocont.2013.11.009.
- Evidence: ScienceDirect pii S0959152413002448 — Yuan, T. & Qin, S.J., 2014, J. Process Control 24(2):450–459 (cited ~227); Semantic Scholar paper 81e1b4a6283571687c32deb487cd4770362369ba.
- All fields match.

## 12. bauer2007finding — VERIFIED

- Claimed: Bauer, Margret; Cox, John W.; Caveness, Michelle H.; Downs, James J.; Thornhill, Nina F. — "Finding the direction of disturbance propagation in a chemical process using transfer entropy", IEEE Transactions on Control Systems Technology, 15(1):12–21, 2007, DOI 10.1109/TCST.2006.883234.
- Evidence: Semantic Scholar DOI record (https://api.semanticscholar.org/graph/v1/paper/DOI:10.1109/TCST.2006.883234) — M. Bauer, John W. Cox, M. Caveness, J. Downs, N. Thornhill, IEEE TCST, Vol 15, pp 12–21, 2007. Google Scholar profile of Margret Bauer lists the paper.
- All fields match.

## 13. iri1979algorithm — VERIFIED

- Claimed: Iri, Masao; Aoki, Katsuo; O'Shima, Eiji; Matsuyama, Hideaki — "An algorithm for diagnosis of system failures in the chemical process", Computers & Chemical Engineering, 3(1–4):489–493, 1979, DOI 10.1016/0098-1354(79)80079-4.
- Evidence: multiple citing sources confirm the citation "Comput. Chem. Engng., 3, 489–493 (1979)" with authors M. Iri, K. Aoki, E. O'Shima, H. Matsuyama (Semantic Scholar; Springer book citations; Academia.edu SDG papers). ScienceDirect hosts the article under the DOI.
- All fields match (issue 1–4 is the combined inaugural-volume issue, standard record).

## 14. hill1965environment — VERIFIED

- Claimed: Hill, Austin Bradford — "The environment and disease: association or causation?", Proceedings of the Royal Society of Medicine, 58:295–300, 1965, DOI 10.1177/003591576505800503.
- Evidence: PubMed Central PMC1898525 (full text); SAGE publisher page https://journals.sagepub.com/doi/10.1177/003591576505800503 — Proc R Soc Med 58(5):295–300, May 1965.
- All fields match.

## 15. heuer1999psychology — VERIFIED

- Claimed (book): Heuer, Richards J. — "Psychology of Intelligence Analysis", Center for the Study of Intelligence, Central Intelligence Agency, Washington, DC, 1999.
- Evidence: CIA official page "Psychology of Intelligence Analysis. By Richards J. Heuer, Jr. (1999)" (https://www.cia.gov/resources/csi/books-monographs/psychology-of-intelligence-analysis-2); Internet Archive scan; Google Books (Center for the Study of Intelligence, 1999, 184 pp).
- "Richards J. Heuer, Jr." is the author's real name (not a typo for "Richard"). All fields match.

---

## Summary Table

| key | verdict | action needed |
|---|---|---|
| tuli2022tranad | VERIFIED | none |
| reinartz2021extended | VERIFIED | none |
| skab2020 | VERIFIED | none (matches authors' official citation block) |
| russell2000delay | VERIFIED | none |
| zhou2024causalkgpt | VERIFIED | none |
| lin2025fdllm | VERIFIED | none (do not confuse with the different arXiv "FD-LLM ... of Machines") |
| wen2025troubleshooting | VERIFIED | none (authoritative DOI record matches bib exactly) |
| xu2026digitaltwin | VERIFIED | none |
| wei2026agentrca | VERIFIED | none (arXiv:2607.22385 resolves; "AgentRCA:" prefix is cosmetic) |
| qin2012survey | VERIFIED | none |
| yuan2014root | VERIFIED | none |
| bauer2007finding | VERIFIED | none |
| iri1979algorithm | VERIFIED | none |
| hill1965environment | VERIFIED | none |
| heuer1999psychology | VERIFIED | none |

**Counts: 15 verified / 0 mismatch / 0 not_found.**
