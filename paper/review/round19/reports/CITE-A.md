# Citation Integrity Audit — Batch A (refs.bib)

Auditor: citation-integrity check, round 19. Date: 2026-09-19.
Method: full bib entry read → web search (title + first author) → DOI resolution via Crossref/DataCite/arXiv APIs. Every DOI below was resolved against its registry (Crossref for journal/book DOIs, DataCite for the Harvard Dataverse dataset DOI, arXiv for preprints).

**Verdict summary: 16 VERIFIED / 0 MISMATCH / 0 NOT_FOUND. No fabricated references found in Batch A.**

---

## 1. downs1993plant — VERIFIED

- Claimed: Downs, James J. and Vogel, Ernest F., "A plant-wide industrial process control problem", Computers & Chemical Engineering, 17(3), 245–255, 1993, DOI 10.1016/0098-1354(93)80018-I.
- Evidence: ScienceDirect publisher page (PII 009813549380018I = the claimed DOI), vol. 17(3), pp. 245–255, 1993. https://www.sciencedirect.com/science/article/pii/009813549380018I
- All fields match. Action: none.

## 2. chiang2001fault — VERIFIED

- Claimed: Chiang, Russell, Braatz, "Fault Detection and Diagnosis in Industrial Systems", Springer, London, 2001, DOI 10.1007/978-1-4471-0347-9.
- Evidence: Crossref record for 10.1007/978-1-4471-0347-9 — book, authors Leo H. Chiang / Evan L. Russell / Richard D. Braatz, Springer London, 2001. https://api.crossref.org/works/10.1007/978-1-4471-0347-9 ; also Springer link.springer.com and Google Books.
- All fields match. Action: none.

## 3. rieth2017additional — VERIFIED

- Claimed: Rieth, Amsel, Tran, Cook, "Additional Tennessee Eastman Process Simulation Data for Anomaly Detection Evaluation", Harvard Dataverse, V1, 2017, DOI 10.7910/DVN/6C3JR1.
- Evidence: DataCite registry record for 10.7910/DVN/6C3JR1 — exact title, creators Cory A. Rieth / Ben D. Amsel / Randy Tran / Maia B. Cook, publisher Harvard Dataverse, 2017. https://api.datacite.org/dois/10.7910/DVN/6C3JR1 ; DOI redirects to https://dataverse.harvard.edu/citation?persistentId=doi:10.7910/DVN/6C3JR1 ; also indexed on Semantic Scholar.
- All fields match (title-case "{Tennessee} {Eastman}" braces are LaTeX protection only). Action: none.

## 4. khan2024faultexplainer — VERIFIED

- Claimed: Khan, Nahar, Chen, Constante-Flores, Li, "FaultExplainer: Leveraging Large Language Models for Interpretable Fault Detection and Diagnosis", Computers & Chemical Engineering, 199, 109152, 2025, DOI 10.1016/j.compchemeng.2025.109152, preprint arXiv:2412.14492.
- Evidence: Crossref record — exact title, authors Abdullah Khan / Rahul Nahar / Hao Chen / Gonzalo E. Constante Flores / Can Li, C&E Chem. Eng. vol. 199, art. 109152, 2025 (August). https://api.crossref.org/works/10.1016/j.compchemeng.2025.109152 ; arXiv preprint 2412.14492 confirmed (Dec 2024).
- All fields match. Cosmetic (non-blocking): publisher renders "Constante Flores" unhyphenated vs bib "Constante-Flores"; bib key says 2024 while year=2025 (key naming only, matches arXiv preprint year). Action: none required.

## 5. pozdnyakov2024adversarial — VERIFIED

- Claimed: Pozdnyakov, Kovalenko, Makarov, Drobyshevskiy, Lukyanov, "Adversarial Attacks and Defenses in Fault Detection and Diagnosis: A Comprehensive Benchmark on the Tennessee Eastman Process", IEEE Open Journal of the Industrial Electronics Society, 5, 428–440, 2024, DOI 10.1109/OJIES.2024.3401396.
- Evidence: Crossref record — exact title, authors Vitaliy Pozdnyakov / Aleksandr Kovalenko / Ilya Makarov / Mikhail Drobyshevskiy / Kirill Lukyanov, IEEE OJIES vol. 5, pp. 428–440, 2024. https://api.crossref.org/works/10.1109/OJIES.2024.3401396 ; arXiv preprint (Mar 2024) and GitHub "fdd-defense" corroborate.
- All fields match, including the second author's given name "Aleksandr" (an earlier search snippet's "Aleksei" was a summarizer artifact; Crossref confirms Aleksandr). Action: none.

## 6. hartung2023deep — VERIFIED

- Claimed: 18 authors (Hartung … Kloft), "Deep Anomaly Detection on Tennessee Eastman Process Data", Chemie Ingenieur Technik, 95(7), 1077–1082, 2023, DOI 10.1002/cite.202200238.
- Evidence: Crossref record — exact title, venue Chemie Ingenieur Technik 95(7):1077–1082, 2023; full author list matches bib in order: Hartung, Franks, Michels, Dennis Wagner, Philipp Liznerski, Steffen Reithermann, Sophie Fellenz, Fabian Jirasek, Maja Rudolph, Daniel Neider, Heike Leitte, Chen Song, Benjamin Kloepper, Stephan Mandt, Michael Bortz, Jakob Burger, Hans Hasse, Marius Kloft. https://api.crossref.org/works/10.1002/cite.202200238 ; arXiv 2303.05904.
- All fields match. Action: none.

## 7. iliopoulos2023detection — VERIFIED

- Claimed: Iliopoulos, Violos, Diou, Varlamis, "Detection of Anomalies in Multivariate Time Series Using Ensemble Techniques", 2023 IEEE Ninth International Conference on Big Data Computing Service and Applications (BigDataService), 1–8, 2023, DOI 10.1109/BigDataService58306.2023.00007.
- Evidence: Crossref record — exact title, all four authors, container "2023 IEEE Ninth International Conference on Big Data Computing Service and Applications (BigDataService)", pp. 1–8, 2023. https://api.crossref.org/works/10.1109/BigDataService58306.2023.00007 ; IEEE Xplore and arXiv preprint corroborate.
- All fields match. Action: none.

## 8. vieira2026towards — VERIFIED

- Claimed: Vieira, Bauler, Rosa, Silva, "Towards a more realistic evaluation of machine learning models for bearing fault diagnosis", Mechanical Systems and Signal Processing, 258, 114640, 2026, DOI 10.1016/j.ymssp.2026.114640.
- Evidence: Crossref record — exact title, authors João Paulo Vieira / Victor Afonso Bauler / Rodrigo Kobashikawa Rosa / Danilo Silva, MSSP vol. 258, art. 114640, 2026 (August). https://api.crossref.org/works/10.1016/j.ymssp.2026.114640 ; arXiv version (2025) and Google Scholar profile confirm.
- All fields match. Action: none.

## 9. hendriks2022towards — VERIFIED

- Claimed: Hendriks, Dumond, Knox, "Towards better benchmarking using the CWRU bearing fault dataset", Mechanical Systems and Signal Processing, 169, 108732, 2022, DOI 10.1016/j.ymssp.2021.108732.
- Evidence: NASA ADS bibcode 2022MSSP..16908732H; ScienceDirect S0888327021010499; Semantic Scholar. Title, authors (Jacob Hendriks, Patrick Dumond, David A. Knox), vol. 169, art. 108732, 2022 all confirmed.
- All fields match. Action: none.

## 10. liu2025spatial — VERIFIED

- Claimed: Liu, Xu, Zhao, Song, He, "Spatial-temporal adaptive causality graph-based fault root cause location method for time-varying industrial process", Advanced Engineering Informatics, 68, 103765, 2025, DOI 10.1016/j.aei.2025.103765.
- Evidence: Crossref record — exact title, authors Yan Liu / Zuhua Xu / Jun Zhao / Chunyue Song / Zhijing He, AEI vol. 68, art. 103765, 2025 (November). https://api.crossref.org/works/10.1016/j.aei.2025.103765 ; ScienceDirect + SSRN preprint corroborate.
- All fields match. Action: none.

## 11. yue2023root — VERIFIED

- Claimed: Yue, Chai, Wan, Xie, Chen, Gui, "Root cause analysis for process industry using causal knowledge map under large group environment", Advanced Engineering Informatics, 57, 102057, 2023, DOI 10.1016/j.aei.2023.102057.
- Evidence: Crossref record — exact title, authors Weichao Yue / Jianing Chai / Xiaoxue Wan / Yongfang Xie / Xiaofang Chen / Weihua Gui, AEI vol. 57, art. 102057, 2023 (August). https://api.crossref.org/works/10.1016/j.aei.2023.102057
- All fields match. Action: none.

## 12. liu2024label — VERIFIED

- Claimed: Liu, Zheng, Liu, Jia, Tan, "Label-free evaluation for performance of fault diagnosis model on unknown distribution dataset", Advanced Engineering Informatics, 62, 102912, 2024, DOI 10.1016/j.aei.2024.102912.
- Evidence: Crossref record — exact title, authors Zhenyu Liu / Haowen Zheng / Hui Liu / Weiqiang Jia / Jianrong Tan, AEI vol. 62, art. 102912, 2024 (October). https://api.crossref.org/works/10.1016/j.aei.2024.102912
- All fields match. Action: none.

## 13. liu2025probing — VERIFIED

- Claimed: Liu, Song, Tang, Wang, Zhu, Cai, "Probing a novel machine tool fault reasoning and maintenance service recommendation approach through data-knowledge empowered LLMs integrated with AR-assisted maintenance guidance", Advanced Engineering Informatics, 66, 103460, 2025, DOI 10.1016/j.aei.2025.103460.
- Evidence: Crossref record — exact full title (including trailing "AR-assisted maintenance guidance"), authors Changchun Liu / Jiaye Song / Dunbing Tang / Liping Wang / Haihua Zhu / Qixiang Cai, AEI vol. 66, art. 103460, 2025 (July). https://api.crossref.org/works/10.1016/j.aei.2025.103460
- All fields match. Action: none.

## 14. gong2026harnessing — VERIFIED

- Claimed: Gong, Qiao, Cao, Tan, Ye, Liu, Chen, Wang, "Harnessing collective intelligence of multi-agent LLM systems for sensor failure reasoning in smart manufacturing", Journal of Industrial Information Integration, 49, 101012, 2026, DOI 10.1016/j.jii.2025.101012.
- Evidence: Crossref record — exact title, authors Wei Gong / Shuang Qiao / Chenhong Cao / Shilei Tan / Junliang Ye / Haoxiang Liu / Si Chen / Xuesong Wang, JII vol. 49, art. 101012, 2026 (January). https://api.crossref.org/works/10.1016/j.jii.2025.101012 ; DBLP (J. Ind. Inf. Integr. 49: 101012, 2026) and CityU Scholars corroborate.
- All fields match. Action: none.

## 15. constantinides2025failuresensoriq — VERIFIED

- Claimed (misc): Constantinides, Patel, Lin, Guerrero, Patil, and others, "FailureSensorIQ: A Multi-Choice QA Dataset for Understanding Sensor Relationships and Failure Modes", 2025, arXiv:2506.03278, DOI 10.48550/arXiv.2506.03278.
- Evidence: arXiv abstract page 2506.03278 (submitted 3 Jun 2025) — exact title; full author order Christodoulos Constantinides, Dhaval Patel, Shuxin Lin, Claudio Guerrero, Sunil Dagajirao Patil, Jayant Kalagnanam. https://arxiv.org/abs/2506.03278 ; also accepted at NeurIPS Datasets & Benchmarks track.
- All fields match; the 6th author (Kalagnanam) is correctly covered by "and others". Action: none. (Optional: could upgrade to the NeurIPS D&B entry, but the @misc form is accurate as cited.)

## 16. agentic2025review — VERIFIED

- Claimed: Jiang, Xie, Wang, Yang, Zhou, Yao, Zhu, "Agentic AI for Safety-Aware Process Monitoring and Fault Diagnosis: A Review", Processes, 14(13), 2112, 2026, DOI 10.3390/pr14132112.
- Evidence: Crossref record — exact title, authors Xiaoyu Jiang / Haotao Xie / Jiayu Wang / Zeyu Yang / Yuanqiang Zhou / Le Yao / Zheren Zhu, Processes vol. 14, issue 13, art. 2112, 2026 (published 29 Jun 2026). https://api.crossref.org/works/10.3390/pr14132112 ; cross-confirmed via Semantic Scholar API (DOI:10.3390/pr14132112 — title/venue/year match).
- Note: published June 2026, hence thin coverage in general web search engines; the DOI registry and Semantic Scholar both confirm existence and all metadata. All fields match. Action: none.

---

## Summary Table

| Key | Verdict | Action needed |
|---|---|---|
| downs1993plant | VERIFIED | none |
| chiang2001fault | VERIFIED | none |
| rieth2017additional | VERIFIED | none |
| khan2024faultexplainer | VERIFIED | none (cosmetic: "Constante-Flores" vs publisher's unhyphenated "Constante Flores") |
| pozdnyakov2024adversarial | VERIFIED | none |
| hartung2023deep | VERIFIED | none |
| iliopoulos2023detection | VERIFIED | none |
| vieira2026towards | VERIFIED | none |
| hendriks2022towards | VERIFIED | none |
| liu2025spatial | VERIFIED | none |
| yue2023root | VERIFIED | none |
| liu2024label | VERIFIED | none |
| liu2025probing | VERIFIED | none |
| gong2026harnessing | VERIFIED | none |
| constantinides2025failuresensoriq | VERIFIED | none (optional: cite NeurIPS D&B version) |
| agentic2025review | VERIFIED | none |

**Counts: 16 verified / 0 mismatch / 0 not-found. Batch A is fully clean — no fabricated or misattributed references detected.**
