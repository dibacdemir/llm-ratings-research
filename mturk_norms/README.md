# mturk_norms — sentence/word-rating data converted from the TedLab MTurk export

Converted from `raw-data/MTURK_export_2026-07-15.zip`, then **repaired on 2026-08-20**
following the audit in [`../audit/DATA_AUDIT_2026-08-19.md`](../audit/DATA_AUDIT_2026-08-19.md).
Question wording and response-scale labels come from `raw-data/_WORDING.zip`
(a reconstruction from the live MTurk Requester dashboard + recovered local HIT
templates), since the batch-CSV export itself never contained them.

## What's here

- `norm_datasets/<experiment>.csv` — one file per experiment folder, columns
  `unit, mean, std, n, individual_ratings` (`unit` = the rated text, HTML stripped;
  `std` = **sample SD, ddof=1**; `mean` recomputable from `individual_ratings`).
- `instructions/<experiment>_i.txt` — the rating prompt: dimension-specific question,
  the study's **verbatim recovered scale labels on every point**
  (`1 = Extremely unnatural … 5 = Extremely natural`), "Answer with one digit.",
  stimulus as `<<{sentence}>>` (or `<<{word}>>` for the 29 word/phrase-unit sets:
  `massive_mem_*`, `copy_of_verb_causality_*`/`verb_causality_semantics`, `word3_*`).
- `a_index.csv` — one row per dataset with `status`, `dimension`, `scale`,
  `scale_labels` (verbatim, `|`-joined), `placeholder`, and per-dataset
  `question_provenance` / `scale_source` documenting exactly where each instruction's
  wording came from (dashboard row, catalog, template, or reconstruction) — **read this
  before publishing any dataset**.
- `non_english/` — non-English datasets, same layout (`norm_datasets/` +
  `instructions/`): currently only `pascal_1_dec_2012` (French sentences, French
  instruction). Kept apart so the main tree is uniformly English; the `language`
  column in `a_index.csv` records each dataset's language.
- `_remaining_classification.csv` — legacy triage of all 2,853 raw CSVs (pre-repair
  bookkeeping; counts are approximate).

## Yield (post-repair)

**169 datasets** (2011–2021): **153 usable** + **16 blocked** awaiting wording from
collaborators (`status=blocked_missing_wording`; list and repair recipe in
[`../audit/BLOCKED_MISSING_WORDING.md`](../audit/BLOCKED_MISSING_WORDING.md) — the
blocked files are untouched and still carry every pre-audit defect).
Totals: **55,365 units, 1,711,901 individual ratings**. Scales: 1–5 (136), 1–7 (24),
1–3 (9). Two audio-stimulus datasets (`..._marie_expt3*`) were dropped entirely
(units were `.aiff` filenames).

## 2026-08-20 repair (summary)

1. **Instructions rebuilt for all 153 usable sets** from the recovered wording:
   dimension-specific questions, verbatim all-point scale labels, no meta text,
   correct placeholder, French for the French survey. Scale labels are *recovered*;
   the interrogative phrasing of the question is usually *reconstructed* (the
   dashboard stores layouts, rarely literal question sentences) — see
   `question_provenance`.
2. **11 datasets re-converted from raw**: `erp_norming_error_detection_june_2013_4`
   (ratings were attached to the unpresented grammatical controls; now keyed to the
   presented `trial_2` stimuli), `verb_causality_study_syntax` (11 silently dropped
   batch files recovered), `verb_causality_study_semantics` (2 dropped batches
   recovered), and 7 context-design sets re-keyed to full context+target units,
   un-pooling ratings that had been averaged across experimental conditions
   (`imperative_control_iad_gs`, `..._for_gs_may_11_2011`, `cul_jack_april_12_2012_54`,
   `word_length_context...`, `acd_v1`, `acd_v6`, `for_jkm_jan_2012`); plus a mojibake
   repair in `orange_camel...`.
3. **`std` recomputed as sample SD (ddof=1)** everywhere (was undocumented ddof=0).

## Caveats

1. **Question wording is largely reconstructed** (scale labels are not — they are
   verbatim dashboard recoveries). `a_index.csv` flags the datasets where the
   dimension itself rests on folder-name convention or sibling inference; a further
   list of scale assignments awaiting collaborator confirmation is in
   [`../audit/REMAINING_FIXES.md`](../audit/REMAINING_FIXES.md).
2. **No participant exclusions / attention-check filtering** applied, with one
   exception: the 10 button-catch trial units ("Choose the leftmost button." etc.)
   were removed from `mk_grammaticality_study_7_20` on 2026-08-20 (their means
   tracked button position, not grammaticality).
3. **No filler annotation**: the export does not mark fillers, so unlike
   `surveyor_norms` there is no `item_type` column here.
4. **Overlap with published norms**: `massive_mem_*` word lists overlap up to 63%
   with `norm_datasets/` (brysbaert2014, warriner2013, kuperman2012, lancaster2020…),
   including same-dimension pairs — do not treat them as independent.
5. **Not de-identified** (folder names contain researcher names; raw CSVs contain
   WorkerIds). Scrub before release.
6. **`verb_causality_study_syntax`** now includes all 15 batch lists; ~70% of its
   units have n≤4 (each recovered list ran few workers) — check `n` before item-level
   analyses.
