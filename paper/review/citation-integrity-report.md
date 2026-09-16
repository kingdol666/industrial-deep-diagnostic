# Bibliographic Integrity Report — `paper/refs.bib`

> Stage 2.5 (INTEGRITY) of the academic pipeline, applied to the AEI submission.
> Method: **publisher-deposited registry records**, not citation aggregators that
> mirror the BibTeX under test. DOIs were resolved against the Crossref REST API
> (`api.crossref.org/works/<doi>`) and, for datasets and preprints, the DataCite
> API (`api.datacite.org/dois/<doi>`). arXiv IDs were fetched from `arxiv.org/abs/`.
> Print-only works were checked via OpenLibrary / Europe PMC.
>
> Reproduce the machine-checkable part with:
> ```bash
> node baseline-lab/scripts/check-bib.mjs paper/refs.bib    # structure gate
> node baseline-lab/scripts/verify-refs.mjs paper/refs.bib  # DOI resolution + title match
> ```

## Headline result

| Metric | Before | After |
|---|---|---|
| Entries | 41 | 41 |
| DOIs that resolve **and match the cited title** | 29 | **40** |
| DOIs resolving to a **different paper** | **7** | 0 |
| Entries with no evidence of existence | **1** | 0 |
| Cited-but-undefined keys | 0 | 0 |
| BibTeX build warnings | 4 (incl. 8 syntax errors) | 1 (benign) |

**The dominant defect was not missing references but DOIs that resolved to
entirely different papers** — evidently generated rather than copied from the
publisher record. Seven were found. One reference could not be shown to exist at
all. All are now corrected or replaced.

## Corrections applied

### DOIs that resolved to a different work (7)

| Key | Was | Now | Evidence |
|---|---|---|---|
| `qin2012survey` | `10.1016/j.jprocont.2011.12.012` → resolved to a *batch quality control* paper; wrong journal, volume, pages | `10.1016/j.arcontrol.2012.09.004`; *Annual Reviews in Control* **36**(2):220–234 | [Crossref](https://api.crossref.org/works/10.1016/j.arcontrol.2012.09.004) |
| `yuan2014root` | `10.1016/j.jprocont.2014.01.006` → resolved to a *building-control* paper | `10.1016/j.jprocont.2013.11.009` | [Crossref](https://api.crossref.org/works/10.1016/j.jprocont.2013.11.009) |
| `bauer2007finding` | `10.1021/ie070972z` → 404. **Also wrong title, journal, volume, pages and an author initial** | Full rewrite: *IEEE Trans. Control Systems Technology* **15**(1):12–21, `10.1109/TCST.2006.883234` | [Crossref](https://api.crossref.org/works/10.1109/TCST.2006.883234) |
| `iri1979algorithm` | `…0098-1354(79)80038-0` → 404 | `10.1016/0098-1354(79)80079-4` | [Crossref](https://api.crossref.org/works/10.1016/0098-1354(79)80079-4) |
| `morbach2009ontocape` | `…compchemeng.2009.04.019` → 404 | `10.1016/j.compchemeng.2009.01.019` | [Crossref](https://api.crossref.org/works/10.1016/j.compchemeng.2009.01.019) |
| `goldrick2019modern` | `…compchemeng.2019.01.011` → resolved to a *patent-ranking* paper; wrong volume, pages, and a 10-author list matching no indexed version | Vol **130**:106471, `10.1016/j.compchemeng.2019.05.037`, 6 authors | [Crossref](https://api.crossref.org/works/10.1016/j.compchemeng.2019.05.037) |
| `indpensim2020` | `10.17632/pdnjz7zz5x.1` → a *different* Mendeley deposit (single creator); the cited author list matches nothing | **Replaced** by the canonical simulator paper: Goldrick et al., *J. Biotechnology* **193**:70–82 (2015), `10.1016/j.jbiotec.2014.10.029`; key renamed `goldrick2015development` | [Crossref](https://api.crossref.org/works/10.1016/j.jbiotec.2014.10.029) |

### Reference that could not be shown to exist (1)

`goldenberg2019fault` — "Comparison of multivariate statistical process
monitoring methods monitoring the Tennessee Eastman process", IFAC-PapersOnLine
52(1):476–481 (2019). Exhaustive search found **no record**: Crossref
bibliographic and author queries; a journal-scoped Crossref sweep of
IFAC-PapersOnLine (ISSN 2405-8963) for 2019 (two Tennessee-Eastman hits, neither
matching); Crossref `author=Goldenberg` + `title=Tennessee Eastman` (zero hits);
and an exact-quoted-title web search. Every channel returned only a *different*
paper.

It was cited **three times**, including in the Related Work table, so it could not
simply be dropped. It was **replaced with the work the sentence actually needs** —
the canonical PCA-versus-Eastman comparison, verified via Crossref:

> Kano, M., Nagao, K., Hasebe, S., Hashimoto, I., Ohno, H., Strauss, R., &
> Bakshi, B. R. (2002). *Comparison of multivariate statistical process
> monitoring methods with applications to the Eastman challenge problem.*
> Computers & Chemical Engineering **26**(2):161–174.
> [10.1016/S0098-1354(01)00738-4](https://api.crossref.org/works/10.1016/S0098-1354(01)00738-4)

Key renamed `goldenberg2019fault` → `kano2002comparison`, with all three citation
sites updated.

### Metadata corrections to real works (5)

| Key | Correction | Evidence |
|---|---|---|
| `hendriks2022towards` | volume `209` → **`169`**; author `Hendriks, Jasper` → **`Jacob`** | [Crossref](https://api.crossref.org/works/10.1016/j.ymssp.2021.108732) |
| `rieth2017additional` | author `Rieth, Carrie A.` → **`Cory A.`**; it is a **dataset**, not an article (now `@misc` with `publisher`/`version`); key renamed to the correct year 2017 | [DataCite](https://api.datacite.org/dois/10.7910/DVN/6C3JR1) — creators "Rieth, Cory A.; Amsel, Ben D.; Tran, Randy; Cook, Maia B.", published 2017 |
| `skab2020` | authors `{Katser, Iurii and Kozitsin, Voitsekhovsky}` → **`{Katser, Iurii D. and Kozitsin, Vyacheslav O.}`**; added the dataset DOI and the Kaggle artifact URL (the old `howpublished` pointed at the code repo, not the cited artifact) | [DataCite](https://api.datacite.org/dois/10.34740/KAGGLE/DSV/1693952) — creators "Iurii D. Katser; Vyacheslav O. Kozitsin" |
| `wu2023autogen` | `Wu, Chaoyun` → **`Wu, Yiran`**; `Zhu, Ermon` → **`Zhu, Erkang`** | [arXiv:2308.08155](https://arxiv.org/abs/2308.08155) |
| `hill1965environment` | added DOI `10.1177/003591576505800503`; **dropped** `number = {5}` (PubMed/Europe PMC do not index an issue number, so it could not be corroborated) | [Europe PMC PMID 14283879](https://europepmc.org/article/MED/14283879) |

### Upgraded to peer-reviewed versions (1)

`hartung2023deep` was cited as an arXiv preprint. The peer-reviewed version
exists, so the AEI submission now cites it: *Chemie Ingenieur Technik*
**95**(7):1077–1082 (2023),
[10.1002/cite.202200238](https://api.crossref.org/works/10.1002/cite.202200238) —
same title, same 18-author list.

### Preprints given DataCite-registered DOIs (4)

So that they are machine-verifiable rather than merely plausible:
`wei2026agentrca` (`10.48550/arXiv.2607.22385`), `wu2023autogen`
(`10.48550/arXiv.2308.08155`), `yao2023react` (`10.48550/arXiv.2210.03629`),
`constantinides2025failuresensoriq` (`10.48550/arXiv.2506.03278`).

## Specifically checked, and clean

- **`wei2026agentrca` — arXiv:2607.22385 is NOT fabricated.** This was the
  highest-risk entry (a future-dated ID). It resolves to "Agentic Root Cause
  Analysis through Evidence-Grounded Reasoning", Amaury Wei & Olga Fink,
  submitted 24 Jul 2026, cs.AI.
- `khan2024faultexplainer` already cited the *published* version
  (*Comput. Chem. Eng.* **199**:109152, 2025), not the preprint — correct.
- `agentic2025review` metadata is correct (*Processes* **14**(13):2112, 2026);
  only the BibTeX *key* still says 2025. Left as-is for key stability, noted here.
- `xu2026digitaltwin` and `gong2026harnessing`: a 2025 DOI with a 2026 volume is
  normal Elsevier online-first behaviour, confirmed for both.
- 14/14 floats labelled and referenced; every figure appears after its first
  reference; 84 citation sites over 41 keys, no orphans and no dangling keys.

## Residual, stated rather than hidden

- **`heuer1999psychology`** is the one entry with no DOI. It is a 1999 print
  monograph (CIA Center for the Study of Intelligence), verified through
  OpenLibrary; print monographs legitimately have none.
- **`yao2023react`** has no page numbers — ICLR proceedings do not paginate. This
  is the single remaining BibTeX warning and it is expected.
- **ScienceDirect returns HTTP 403 to automated fetches.** For Elsevier items the
  evidence is the publisher-deposited Crossref record — the publisher's own
  authoritative metadata — corroborated via DataCite or Semantic Scholar wherever
  an author name was in question.
- **`iri1979algorithm` `number = {1--4}`** is retained but unconfirmed: the
  corrected DOI establishes volume 3 and pages 489–493, while Crossref does not
  expose the issue number.
