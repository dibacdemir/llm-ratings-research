# Remaining fixes after the 2026-08-20 repair pass

What the 2026-08-20 repair did **not** resolve, ordered by importance. Sources: the
audit ([`DATA_AUDIT_2026-08-19.md`](DATA_AUDIT_2026-08-19.md), `audit_findings.csv`)
and the repair agents' flagged judgment calls (full provenance per dataset in the two
`a_index.csv` files).

## 1. Blocked: 16 MTurk datasets with no recovered wording

See [`BLOCKED_MISSING_WORDING.md`](BLOCKED_MISSING_WORDING.md). Untouched, still
carry every pre-audit defect (meta-leak, unknown dimension, ddof=0 std, and for
`acd_context_polly` / `cul_jack_60` / `mk_alive|goals|thought` also the §2 unit
defects). Waiting on collaborators.

## 2. Scale/wording assignments to confirm with collaborators (usable but inferred)

For these datasets the scale/question was not recovered for that exact study; the
most likely one was taken from sibling studies in the same series. **Andrea decided
on 2026-08-20 to keep them all usable as-is** (rather than block them), pending
collaborator confirmation. They carry `quality_flag=scale_unconfirmed` in
`mturk_norms/a_index.csv` (17 datasets) so they can be filtered in analyses:

- `acd_project_expt_45_hkv_expt_2_plaus_...` — folder says "plaus", but no
  plausibility scale is recoverable for the ACD family; naturalness used. Confirm.
- `p_p_sentence_naturalness_survey_{june_2013_v3,may_2013,may_2013_v2}` — the only
  recovered in-family scale is a *likelihood* scale despite "naturalness" folder
  names. Confirm which was on the page.
- `noisy_channel_acceptability_{1,2}_sept_2013` — no reliable recovered scale
  (template match incompatible with observed 1–5); 5-pt naturalness used as fallback.
- `isac_..._giant_c{,obra}` (the two 1–7 sets), `reasoning_and_language...` /
  `social_interaction...` (7th label reconstructed), the Denise/Feb-16 7-pt sets,
  `sentence_naturalness_survey_laura_mar_17_...` (7-pt inferred from siblings),
  `quant_syn_april_14_...` (scale via april_13/16 siblings).
- `agreement_norming_nov` — two candidate catalog rows ("Nov 17" naturalness vs
  "Nov 18" likelihood); own dashboard row (naturalness) was used. Confirm.

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
  consider a minimum-n filter at analysis time.
- Placeholder boundary calls: `neal_norming_1` and `agreement_norming_nov` have bare
  NP units currently under `{sentence}` (questions phrased as "phrase") — switch to
  `{word}` if preferred.

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
