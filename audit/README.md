# audit/ — data audit & repair trail

This folder documents the full audit and repair of the three data trees
(2026-08-19 → 2026-08-21). **This README is the only living document here; it
holds the current status, the open items, and the decision log.** The other files
are frozen historical records:

| File | What it is |
|---|---|
| [`DATA_AUDIT_2026-08-19.md`](DATA_AUDIT_2026-08-19.md) | The deep audit of `mturk_norms/` + `surveyor_norms/` against the raw exports, with an appendix on the 16 blocked datasets and their resolution. All issues since fixed. |
| [`audit_findings.csv`](audit_findings.csv) | Machine-readable snapshot of the 389 audit findings **as of 2026-08-19, pre-repair** — the issues it lists are fixed; keep for the paper's methods trail. |
| [`PUBLISHED_SETS_AUDIT_2026-08-21.md`](PUBLISHED_SETS_AUDIT_2026-08-21.md) | Full-row audit of the 20 published reference sets (`norm_datasets/` + `instructions/`), with the applied fixes listed at the end. |

## Current status (2026-08-21)

All three trees are audited, repaired, and verified; **nothing is blocked**:

| Tree | Datasets | Units | Individual ratings | Notes |
|---|---|---|---|---|
| `norm_datasets/` (published) | 20 families / 64 CSVs | — | mixed (some aggregate-only) | ddof=1 where trial-level; all issues fixed except by-decision leftovers below |
| `mturk_norms/` | 167 (166 en + 1 fr) | 54,757 | 1,705,009 | ddof=1; instructions from recovered dashboard wording; provenance per dataset in `a_index.csv` |
| `surveyor_norms/` | 100 (90 en + 10 non-en) | 13,695 | 330,886 | ddof=1; `item_type` column; instructions verbatim from surveys |

## Open items

**Worth doing before publication:**
1. Native-speaker check of the machine-translated instruction *boilerplate* in the
   11 `non_english/` files (Italian ×2, Russian, Mandarin, Finnish, Turkish,
   Portuguese ×4, French). Questions and scale labels are verbatim from the surveys;
   only the "Rate on a scale…" / "Answer with one digit." lines were translated.
2. `tuckute2024`: quote placement in the 4 repaired sentences is reconstructed —
   cross-check against the published materials if those items matter
   (list in `norm_datasets/tuckute2024_data/README_tuckute2024.txt`).

**Analysis-time decisions (not data bugs):**
3. `edwards2024` is direction-inverted relative to its name: high score = harder to
   sound out = LESS transparent.
4. Low-n units: `verb_causality_study_syntax` (~70% of units n≤4),
   `chomsky_items_2` (3 units total) — consider minimum-n filters.
5. `massive_mem_*` overlaps published norms up to 63% (same-dimension pairs, e.g.
   concreteness vs `brysbaert2014`) — not independent samples.
6. L2 speakers retained in `class_demo`, `demo_9_59_2025/2026` (30–45%).
7. `massive_mem_*_end_*` are second waves of the same studies — merge or keep
   separate before publication-level analyses.
8. `gatti2024`: LLM elicitation is single-item 1–9 rating while humans did
   best-worst (documented in its README) — cross-paradigm comparison.
9. Same-text condition pooling in `extension`/`extension_study` (harmless for LLM
   comparison); item overlap between `quantitative_syntax_survey` and
   `chomsky_items_1`.

**Optional polish:**
10. Split `p_p_sentence_naturalness_survey_feb` (two waves, identical scale, pooled
    in one folder — the only remaining silent folder merge, harmless).
11. `orange_camel_...`: units are pre-joined context+target passages; split like the
    re-keyed sets if a target-sentence reading is preferred.
12. `{word}` vs `{sentence}` for bare-NP units (`neal_norming_1`,
    `agreement_norming_nov_17`/`_18`); `winter2017` duplicate unit "down".
13. `pronouns_following_verbs*`: scale labels recovered ("Not strong / Reasonably
    strong / Strong") but the on-page question framing was never recovered.

**Housekeeping:**
14. `mturk_norms/_convert.py` is the pre-repair converter — do **not** re-run it
    (it would reintroduce ddof=0 and the old unit keying).
15. `mturk_norms/_remaining_classification.csv` is stale legacy bookkeeping.
16. `pipeline/experiments.py` still registers only the 20 published families;
    the TedLab trees are ready for auto-discovery via their `a_index.csv`.

## Decision log

- **2026-08-19 — audit.** ~40 agents, adversarially verified (120/121 high findings
  confirmed). Result: arithmetic exact, but instructions fabricated/leaky and 11
  MTurk sets mis-keyed. Findings snapshot: `audit_findings.csv`.
- **2026-08-20 — repair round 1** (policies set by Andrea): std = **ddof=1**
  everywhere; scales rendered with **every point labeled** using recovered verbatim
  labels; "Answer with one digit."; `{word}` for word-unit sets; instructions in the
  survey's own language; **fillers included and marked** (`item_type`, surveyor);
  the 41×2 **biased anchor items dropped**; Mac-Roman "décor" repaired; 11 MTurk
  sets re-converted (ERP re-key, dropped batches recovered, context+target
  re-keying); 2 audio datasets dropped; button-catch units removed from
  `mk_grammaticality`; 11 non-English datasets moved to `non_english/`.
  16 MTurk sets remained blocked on missing HIT wording.
- **2026-08-21 — repair round 2** (collaborators' `raw-data/RESOLVED_QUERIES.md`):
  all 16 blocked sets resolved — 12 repaired; `chomsky_items` split into `_1`/`_2`
  and `agreement_norming_nov` split into `_nov_17`/`_nov_18` (both folders had
  silently pooled two projects); 4 dropped by decision (`mk_alive/goals/thought`:
  ratings were confidence about a Yes/No judgment; `melissa_transitivity_semantics`:
  rating question unidentifiable). Of the 17 flagged scale guesses: 13 confirmed,
  2 corrected (`p_p_*_may_2013` pair → naturalness), 2 superseded by the splits.
  Folder-merge sweep of all 165 folders found only `p_p_..._feb` (harmless).
  Identifier-level provenance (BatchIds/HITTypeIds): appendix of
  `DATA_AUDIT_2026-08-19.md`.
- **2026-08-21 — published sets**: audited (13/20 clean, zero numeric errors);
  fixes applied per Andrea: `tuckute2024` 40-row repair + README, `troche2014`
  renames, `muraki2023` empty-row drop + instruction alignment, `warriner2013`
  duplicate deletion, README refreshes, `gatti2024` instructions rewritten as
  single-item 1–9 ratings. **Left untouched by decision:** `edwards2024`; the
  pipeline registry (aggregate-only and continuous-scale norms are valid rating
  data for means-level comparison — "excluded" refers only to the trial-level
  distribution pipeline).

## Surveyor instruction preambles (diagnosed 2026-08-21, implementation pending)

A collaborator flagged that the surveyor instructions ignore the participant
preamble in `_demographics.csv`. Verdict: current instructions are verbatim from
stimuli prompt+options (verified 100/100), NOT made up, but the preamble is a real
omission for 48/100 surveys (esp. the 41 discourse sets, whose preambles define
the dimension with examples). Full diagnosis:
`SURVEYOR_INSTRUCTION_DIAGNOSIS_2026-08-21.md`; per-survey table:
`surveyor_instruction_provenance.csv`. **Approved next step (not yet executed):**
rebuild all 100 instructions with the verbatim preamble minus procedural lines
(trims logged). Bonus caveat found: `missing_vp` sibling surveys have OPPOSITE
scale polarity (extension/rereplication 1=easy..5=hard; 0501_final 1=hard..5=easy)
— align before pooling. 7 layout rewords ("above"->"below", bold->positional)
applied 2026-08-21.
