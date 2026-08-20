# Deep data audit — mturk_norms & surveyor_norms vs. raw exports (2026-08-19)

**Scope.** All 271 converted datasets (171 `mturk_norms/`, 100 `surveyor_norms/`) audited
against the raw sources in `raw-data/` (`MTURK_export_2026-07-15.zip`,
`surveyor_export.zip`), plus a light spot-check of the 20 published reference datasets.

**Method.** Multi-agent audit: (1) independent numeric re-derivation of every dataset from
the raw exports, implemented from first principles without reading the original converter;
(2) per-dataset instruction-faithfulness audits against raw metadata (MTurk HIT
Title/Description; surveyor `_stimuli.csv` prompts/options and `_parameters.json`);
(3) repo-wide convention/pipeline checks; (4) a claims-check of the pre-existing
`AUDIT_REPORT.md` and READMEs; (5) adversarial verification: every dataset-specific
high-severity finding was independently re-checked by a second agent instructed to refute
it (120/121 high findings CONFIRMED, 1 downgraded). The two headline re-derivation
findings (ERP stimulus-family swap, Mac-Roman "décor" corruption) were additionally
verified by hand at the byte level.

**Machine-readable findings:** [`audit_findings.csv`](audit_findings.csv) — 389 findings
(121 high / 49 medium / 219 low) across 143 datasets; 128 datasets clean apart from the
two known global issues.

**This report supersedes the root `AUDIT_REPORT.md`, several of whose claims are false
(see §6).**

---

## 1. The arithmetic is essentially perfect — the semantics often are not

Independent re-derivation reproduced the converted numbers essentially exactly:

- **MTurk (171/171):** unit sets, per-unit n, rating multisets, means and stds all
  identical to the converted CSVs (README totals 54,498 units / 1,722,570 ratings
  confirmed). Index-identity pairing (`Answer.RatingN` ↔ `Input.trial_N`) verified with
  ±1-shift probes (shifting collapses between-item variance, e.g. η² 0.575 → 0.034).
- **Surveyor (100/100):** every rating multiset identical; rating column is `response`
  (leading integer of the option label); no participant was dropped anywhere; no dataset
  pools different response scales.
- `std` is **population SD (ddof=0)** in all 271 files. Consistent but undocumented, and
  differs from the usual norm-dataset convention (ddof=1). Document or recompute.

The serious problems are in **what the numbers are attached to** (§2) and **what the
instructions claim was asked** (§3–4).

## 2. High-severity conversion defects (MTurk) — ratings attached to the wrong text

These are the worst issues found; all verified, all but two fixable from raw.

| Dataset(s) | Defect | Fixable? |
|---|---|---|
| `erp_norming_error_detection_june_2013_4` | **Ratings attached to the wrong stimulus family.** Units are `Input.trial_1_` (grammatical control versions); what workers actually saw and rated is `Input.trial_2_` (error/no-error versions, 323 distinct, counterbalanced). Verified: 0 rated stimuli appear among the 162 units; item-agreement statistics are below chance under the current alignment (ω²=−0.005) and normal under `trial_2_` (ω²=0.292). | **Yes** — re-key on `trial_2_` |
| `verb_causality_study_syntax_ratings_mk_april_2010` | **11 of 15 batch files silently dropped** (those files reuse `Answer.Rating63–82` for a correct/incorrect comprehension task, breaking the converter's index matching). | **Yes** — pair `Rating1–62` only |
| `imperative_control_iad_gs_may_16_2011_purple_puppy`, `sentence_naturalness_survey_for_gs_may_11_2011_purple_puppy` | **Rated sentence missing from unit; conditions pooled.** Units are context passages truncated at a colon; the imperative actually rated (`trial_2_`) is absent, and 96 (resp. 72) distinct context+target items are pooled into 49 (resp. 48) units. | **Yes** |
| `cul_jack_april_12_2012_54...`, `cul_jack_april_2012_60...` | **Coarse units pool ~3.5 targets each**: unit is the context passage; the manipulated target sentence (210 distinct) is discarded. | **Yes** |
| `mk_alive/goals/thought_corpus_questionnaire` (3) | **Target-NP markup stripped**: raw `<u>/<b>` marks which NP was rated; stripping deletes it and 11 units/file merge ratings for two different target NPs. | **Yes** — reinsert marking from `Input.TargetNP` |
| `acd_context_polly_1_nov_23_2012` (+3 siblings with inconsistent policy) | **Dialogue context dropped**: humans rated Mary's reply after a two-turn context; converted unit keeps only the reply, and 83/225 targets pool ratings across different-context conditions. | **Yes** — re-key on (context, target) |
| `sentence_naturalness_survey_for_marie_expt3(_b)` (2) | **Units are `.aiff` audio filenames** — an audio-naturalness study; not usable as a text norm. | **No** — needs audio/transcripts, or exclude |
| `verb_causality_study_semantics_ratings_mk_april_2010` | 2/17 batch files dropped (missing `Input.verb62` column); ~12% of responses lost, mostly recoverable. | Partial |
| `word_length_context_sentence_naturalness_survey_april_2011` | Milder context/target pooling (45 pairs pooled). | Yes |

## 3. MTurk instruction problems (repo-wide)

1. **Prompt meta-leak (all 171).** Every instruction contains the literal debug note
   *"(scale inferred from observed responses)"*. Must be removed before any LLM run.
2. **Wrong placeholder (30 datasets, high).** All 171 instructions use `{sentence}`; 30
   datasets (all `massive_mem_*`, the 5 `verb_causality` copies, `melissa_transitivity`,
   `word3_*`, marie audio sets) have single-word/short-phrase units and their own
   instruction text says "the word". Rename to `{word}` (or `{expression}` for multi-word
   `massive_mem` 2013-style names like "Al Pacino").
3. **Missing or made-up dimension (~45 datasets high/medium).** 53 instructions are the
   bare generic "Rate the sentence./passage." For ~23 of these the raw HIT
   Title/Description **does** name the dimension (e.g. `copy_cat_polly_june_2014_v2_1`:
   "30 short texts to be rated for their causality") — fixable, with proposed replacement
   texts recorded per dataset in `audit_findings.csv`. For the rest the export genuinely
   never names what was rated (§5).
4. **No scale endpoint labels (all 171, medium).** "Rate on a scale from 1 to 5." with no
   anchors — scale *direction* is unspecified to the LLM. The HIT HTML that carried the
   labels is not in the export; not fixable from raw (§5), though dimension-conventional
   defaults could be argued per-dataset.
5. **Style divergence (low):** all new instructions say "Answer with one number." vs. the
   canonical "Answer with one digit." (18/20 reference sets); one mojibake unit in
   `orange_camel_...nov_2010`.

## 4. Surveyor issues

Numbers are exact and instructions are broadly faithful (real prompts and scales from
`_stimuli.csv`), but:

1. **Practice/anchor items with embedded suggested answers included as norm units** —
   all 41 `discourse_*`/`coherence_survey_*` datasets include the 2 practice items whose
   response options literally suggested the answer ("…so you might rate them as a 4 or
   5"). Human ratings for those units are instruction-biased and the LLM prompt omits the
   bias text. Fix: drop those units (identifiable from `_stimuli.csv`).
2. **Practice/filler leakage in other sets (≈30 datasets high)** — practice items,
   fillers, or worked examples included as ordinary units in various syntax and semantics
   sets (types `practice_items_leaked`, `filler_items_included`, `filler_leakage`,
   `worked_example_*` in the CSV). Whether fillers *should* be excluded is a design
   decision, but inclusion is currently silent and inconsistent with the published sets.
3. **Mac-Roman encoding corruption (14 datasets)** — raw stimulus byte `0x8e` ("décor")
   stripped to "dcor", so the LLM sees a non-word humans never saw. Verified byte-level;
   fix by decoding those stimuli files as `mac_roman`. (The old AUDIT_REPORT blamed the
   raw data; that is backwards — the raw file is fine.)
4. **No native-language filtering anywhere** — defensible as a uniform policy, but in
   `class_demo`, `demo_9_59_2025/2026` 30–45% of participants report English as L2.
   Worth a caveat or a sensitivity analysis.
5. **Scale-label formatting heterogeneous (49 datasets, low)** — labels present but in
   non-canonical formats, some descending ("7-makes perfect sense … 1-…"); normalizable
   from `_stimuli.csv` options.

## 5. Not fixable from the raw exports — what to request from collaborators

The MTurk export contains only worker rows (`Input.*`, `Answer.*`, Title/Description);
the **HIT HTML templates** (question wording + scale labels) are absent. Needed from the
lab for:

- **Rating-question wording** (dimension genuinely unrecoverable): `50_sentences_noisy_channel_may_25_2011`,
  `50_sentences_with_2_comp_qs_plus_rating_mar_11_2011`, both `cul_jack_april_2012` text
  sets, `agreement_norming_nov`, `chomsky_items`, `acd_project_expt_44`, `mk_alive/goals/
  thought_corpus_questionnaire`, `melissa_transitivity_semantics`, `neal_norming_1`,
  `noisy_rc_norming_oct19`, the 3 `paris_judgments` + `pascal_1` (French), the 3
  `presup_survey_acd` sets, 6 of the `pronouns_following_verbs_*` variants,
  `islands_acceptability_expt_2_dec_2_2012`.
- **Scale endpoint labels** for all 171 MTurk sets (or an agreed convention).
- **Audio stimuli or transcripts** for the two `marie_expt3` sets (else exclude).
- The **original conversion script/log**, to explain a ~25% response drop in
  `verb_causality_study_semantics_ratings_mk_april_2010` and which of 24 batch files fed
  `sentence_naturalness_survey_for_rw_jan_2010`.

## 6. The pre-existing `AUDIT_REPORT.md` is unreliable

Its headline totals check out (271 datasets, 68,275 units, 2,055,760 ratings; no
out-of-range values; no WorkerId leakage), but:

- "Fixed the massive_mem word norms" — wording was fixed, but all 20 still use
  `{sentence}` for word units; 0/171 MTurk instructions use `{word}` at all.
- "Accent bug was upstream in the raw data" — **false**; raw file is Mac-Roman-correct,
  the converter dropped the accent (§4.3).
- Claimed scale distribution 1-5:148 / 1-7:29 / 1-3:9 sums to 186 > 171 (actual:
  138/24/9); "upgraded 108 instructions / 63 generic" matches no real partition (53
  generic); "175 folders converted" matches neither the 171 datasets nor its own
  classification CSV (178).

Recommend deleting or replacing `AUDIT_REPORT.md` with this report.

## 7. Additional analysis-level caveats

- **Contamination/duplication:** `massive_mem_*` word lists overlap up to 63% with the
  published norms in `norm_datasets/` including same-dimension pairs
  (`massive_mem_concreteness` vs `brysbaert2014_concreteness`, valence/arousal vs
  `warriner2013`). 295 dataset pairs share ≥20 units and ≥30% of a norm. Not an error,
  but analyses must not treat them as independent.
- Reference-set housekeeping: `troche2014` CSV/instruction basename mismatches;
  `devarda2023` two-placeholder instruction and `green2025` float ratings (both already
  pipeline-excluded).
- 2011-era duplicate splits (e.g. `massive_mem_*_mar_2013` vs `_end_*` variants) are
  separate HIT waves of the same study; consider merging or documenting.

## 8. Suggested fix order

1. Global mechanical fixes (one script): strip the meta-leak line from all 171 MTurk
   instructions; `{sentence}`→`{word}`/`{expression}` for the 30 word-unit sets;
   "number"→"digit"; document (or recompute) the ddof=0 std convention.
2. Re-convert the §2 datasets from raw (wrong family / dropped batches / pooled units /
   stripped markup / dropped context) — all raw-recoverable.
3. Surveyor: drop the 41×2 biased anchor items; fix the 14 "décor" units via Mac-Roman
   decoding; decide a documented policy on fillers/practice items and L2 participants.
4. Adopt the ~23 dimension-specific instruction rewrites already drafted (in
   `audit_findings.csv` `proposed_fix` column) where Title/Description grounds them.
5. Request the §5 items from collaborators; until then, exclude or flag the
   dimension-unknown datasets rather than prompting an invented dimension.
