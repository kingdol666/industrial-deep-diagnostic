# Round 36 — 终稿通读、DOI 审计与排版终检（2026-09-24）

对象：paper/main.tex 终稿（57 页）+ refs.bib（72 条）。

## A. 参考文献审计（CrossRef API 逐条验证）

- **对账**：正文引用 71 个 key ↔ refs.bib 72 条，全部对齐（sheridan1978human 为未引用残留，bibtex 自动排除）。
- **已有 50 条 DOI 重验**：43 条 Crossref VERIFIED（标题匹配 ≥0.7）；7 条"404/不匹配"逐条排查：
  - rieth2017additional / skab2020 / merkelbach2024multimodal：DataCite DOI（doi.org 实测均解析 ✓）；
  - tuli2022tranad：Crossref 短标题致相似度误报，DOI 正确（PVLDB 15(6)）；
  - **venkatasubramanian2003part2/part3：原 DOI 错误（doi.org 不解析）** → 经 Crossref 检索改为 10.1016/S0098-1354(02)00161-8 / 10.1016/S0098-1354(02)00162-x（vol 27, pp 313-326 / 327-346 匹配）。
- **补全 16 条缺失 DOI**（全部经 Crossref 验证或 arXiv DataCite）：
  bainbridge1983ironies 10.1016/0005-1098(83)90046-8 · parasuraman2010complacency 10.1177/0018720810376055 · horch1999simple 10.1016/s0967-0661(99)00100-8 · bathelt2015revision 10.1016/j.ifacol.2015.08.199 · zhou2019beatgan 10.24963/ijcai.2019/616 · yoon2001statistical 10.1002/aic.690460910 · alcala2009reconstruction 10.1016/j.automatica.2009.02.027 · hagglund1995control 10.1016/0967-0661(95)00164-p · thornhill2007fault 10.1016/j.conengprac.2006.10.011 · dunia1996identification 10.1002/aic.690421011 · zheng2023judging / panickssery2024selfpref / cemri2025mast / doshivelez2017rigorous / lewis2020rag（arXiv DOI）· sheridan1978human 10.21236/ada057655。
- **两条错误条目整体改写**：
  - yin2014review：原条目（J Process Control 24(1):50-62）经 Crossref 证实不存在，系与真实论文混淆 → 改为 Yin, Ding, Xie, Luo, "A Review on Basic Data-Driven Approaches for Industrial Process Monitoring", IEEE TIE 61(11):6418-6428, 2014, DOI 10.1109/TIE.2014.2301773；
  - alfayez2005detection：原期刊字段错误（Applied Acoustics）→ 真实记录为 Proc IMechE Part E: J. Process Mechanical Engineering 219(4):327-344, DOI 10.1243/095440805x33225（标题匹配 1.00）。
- 其余 4 条无 DOI 属正常（heuer CIA 书、GAMP5、MHRA 报告、—）。
- 证据文件：`_doi_verify3.json`（CrossRef 原始返回），已随本目录留存。

## B. 排版终检与修正

1. **Fig.3（trace）距引用 8 页 + 连续 4 页全浮动** → \FloatBarrier 移至 fig:trace 图环境后：Fig.3 落 p23 紧贴 §7.1 引用，全浮动连页解除，全文 58→57 页。
2. Fig.6 白色注释框加高后压住 "flow-plateau window" 标签 → 标签下移至框下，像素复核完整。
3. lewis2020rag 作者名变音符号转义错误（K{"u}ttler → K{\"u}ttler 等），PDF 乱码消除。
4. 关键词行孤词折页 → 缩短 "Competing-hypothesis reasoning"→"Competing hypotheses" + 摘要删 6 个冗余词，孤行消除。
5. 摘要最终 ~236 词（≤250 ✓）。

## C. 终态

57 页；0 错误、0 未定义引用、0 Overfull；10 图全部距首次引用 ≤3 页且渲染完整；15 表无断行溢出；参考文献 71 条全部被引、真实性经 Crossref/DataCite/doi.org 三路验证、除 4 条无 DOI 的书籍/报告外全部带 DOI 且在文中渲染（elsarticle-num）。
