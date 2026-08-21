# Remaining fixes after the 2026-08-20 repair pass

What the 2026-08-20 repair did **not** resolve, ordered by importance. Sources: the
audit ([`DATA_AUDIT_2026-08-19.md`](DATA_AUDIT_2026-08-19.md), `audit_findings.csv`)
and the repair agents' flagged judgment calls (full provenance per dataset in the two
`a_index.csv` files).

## 1. ~~Blocked: 16 MTurk datasets~~ — RESOLVED 2026-08-21

All resolved via the collaborator's `raw-data/RESOLVED_QUERIES.md`: 12 repaired
(incl. `chomsky_items` split into `_1`/`_2`, `agreement_norming_nov` split into
`_nov_17`/`_nov_18`), 4 dropped by decision (`mk_alive/goals/thought` — the ratings
were confidence about a Yes/No judgment; `melissa_transitivity_semantics` — rating
question unidentifiable). Zero blocked datasets remain. See
[`BLOCKED_MISSING_WORDING.md`](BLOCKED_MISSING_WORDING.md).

## 2. ~~Scales to confirm~~ — RESOLVED 2026-08-21

The collaborator's dashboard extraction confirmed 13 of the 17 flagged guesses
verbatim (incl. the reasoning/social 'Neutral' midpoint) and corrected the rest:
`p_p_..._may_2013` and `_may_2013_v2` are 5-pt NATURALNESS (not likelihood —
instructions fixed); `agreement_norming_nov` was two pooled projects (split, see §1);
`acd_project_expt_45` naturalness confirmed. `quality_flag=scale_unconfirmed` is
cleared everywhere; provenance columns now say `dashboard_confirmed
(RESOLVED_QUERIES.md, 2026-08-20)`.

A folder-merge sweep of all 165 source folders (prompted by the agreement case)
found one further pooled folder: `p_p_sentence_naturalness_survey_feb` combines a
Feb-2010 and a Feb-2011 wave — but both used the identical 5-pt naturalness scale,
so pooling is harmless; splitting is optional provenance polish.

## 3. Data-cleaning decisions still open

- ~~`mk_grammaticality_study_7_20` button-catch units~~ — **done 2026-08-20**: the 10
  "Choose/Please click/Select the leftmost/middle/rightmost button" units were
  removed (1,538 → 1,528 units; a_index counts updated).
- `extension` / `extension_study` (surveyor/syntax): low-severity — a few sentences
  appear verbatim under two experimental conditions and their ratings are pooled
  into one row. For LLM prompting identical text is one item, so pooling is
  arguably correct; only relevant if condition-level analyses are ever needed.
- `orange_camel_...`: units are pre-concatenated context+target blobs from the raw
  Input columns; fine as passages, but the instruction asks about the passage as a
  whole — split like the re-keyed sets if a target-sentence reading is preferred.
- `verb_causality_study_syntax`: recovered batches give ~460/653 units n≤4 —
  consider a minimum-n filter at analysis time. Same for `chomsky_items_2` (only 3
  units — the raw study had 3 items; usable but tiny).
- `mturk_norms/_convert.py` (legacy converter) was NOT updated for the repairs:
  re-running it would reintroduce ddof=0 std and the old unit keying. Do not re-run;
  the repair scripts live in the session scratchpad reports.
- `quantitative_syntax_survey` and `chomsky_items_1` share some passage items
  (same source materials, separate MTurk projects) — mind de-duplication in pooled
  analyses.
- Placeholder boundary calls: `neal_norming_1` and the new `agreement_norming_nov_17`
  / `_nov_18` have bare noun-phrase units currently under `{sentence}` (questions
  phrased as "phrase") — switch to `{word}` if preferred.

## 4. Language checks

**2026-08-20:** all 11 non-English datasets were moved into `non_english/`
subfolders (`mturk_norms/non_english/`: `pascal_1_dec_2012` French;
`surveyor_norms/non_english/norm_datasets/syntax/`: `chinese_dative`,
`russian_freezing`, `dative_turkish`, `dative_finnish`, `italian_dative_v2`,
`italian_locative_v7`, `european_portuguese_rc`, `european_portuguese_wh`,
`gabriel_rc`, `gabriel_wh`) and a `language` column was added to both a_index files.

Still open: the instruction *boilerplate* lines ("Rate on a scale…"/"Answer with one
digit.") in those 11 files were machine-translated by the repair agents and deserve
a native-speaker pass. (The questions and scale labels themselves are verbatim from
the surveys.)

## 5. Analysis-level caveats (not data bugs)

- `massive_mem_*` ↔ published-norm overlap (up to 63%, same-dimension pairs) — do
  not treat as independent; consider an exclusion list (pair list in the audit's
  `cross_conventions` detail).
- L2 participants retained in `class_demo`, `demo_9_59_2025/2026` (30–45%).
- `massive_mem_*_end_*` are separate HIT waves of the same studies — decide merge vs
  keep-separate before publication-level analyses.
- 2011-era `pronouns_following_verbs*`: rating question target ("Not strong /
  Reasonably strong / Strong" — strength of *what*, likely the pronoun–verb
  association) is inferred from the scale; on-page framing unrecovered.

## 6. Housekeeping

- `mturk_norms/_remaining_classification.csv` is stale legacy bookkeeping (its
  converted-folder tallies never matched); regenerate or annotate before relying on it.
- `pipeline/experiments.py` still uses the hardcoded 20-dataset registry;
  the repaired trees are ready for auto-discovery via their `a_index.csv`
  (note surveyor's extra `item_type` column and per-dataset `placeholder`).
- Reference-set housekeeping from the audit (`troche2014` basename mismatch,
  `devarda2023` two placeholders, `green2025` float ratings) — untouched, published
  data.
