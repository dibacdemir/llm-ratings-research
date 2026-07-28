# mturk_norms — sentence/word-rating data converted from the MTURK export

Auto-converted from `MTURK_export_2026-07-15.zip` into the same schema as the existing
`norm_datasets/` + `instructions/` in this repo. **Nothing in the original repo (or in
surveyor_norms) was modified**; this is a standalone sibling directory.

## What's here
- `norm_datasets/<experiment>.csv` — one file per experiment folder, columns:
  `unit, mean, std, n, individual_ratings` (`unit` = the rated sentence/word, HTML stripped)
- `instructions/<experiment>_i.txt` — reconstructed prompt (see caveat 2)
- `a_index.csv` — one row per converted experiment (dim, inferred scale, #batch files, #units, #ratings, median n/unit)
- `_needs_review/` — 11 experiments where the auto-detected unit looked like a question (mapping suspect)
- `_remaining_classification.csv` — every one of the 2,853 MTurk CSVs labeled by category (what was and wasn't converted, and why)

## How the conversion works
MTurk stores data "wide": one row per worker, with `Answer.RatingN` = that worker's rating of
the stimulus in `Input.trial_N` (or `Input.sentN`, etc.). We auto-detect, per file, the stimulus
column family whose index set matches the Rating columns, pair `(sentence_N, RatingN)` for every
worker, and aggregate by sentence text **across all batch files in the same experiment folder**
(this naturally dedupes the many re-run batches). Alignment was verified against the raw data.

## Yield
**175 clean experiments (+11 needs-review), 56,976 unique units, 1,780,669 individual ratings.**
This is ~10x the surveyor set. Many are sentence naturalness/acceptability studies; some (e.g.
"Massive mem familiarity/imageability") are classic single-word norms like the published datasets
already in this repo. Scales inferred from responses: 1–5 (148), 1–7 (29), 1–3 (9).

## Classification of ALL 2,853 MTurk CSVs (see _remaining_classification.csv)
| category | files | folders | status |
|---|---|---|---|
| A rating, convertible                | 908 | 307 | **175 folders converted here**; ~120 more are rating-type but had per-file index mismatches — need alignment review |
| B rating, stimulus column unclear    | 113 | 68  | convertible with extra step (locate the stimulus column) |
| C yes/no comprehension               | 343 | 140 | convertible to proportion-correct (like dentella2023 in repo), not a mean rating |
| D memory / reaction-time games       | 39  | 28  | not a rating task — excluded |
| E surveycode only                    | 178 | 112 | real responses live in an external system, not in this export — cannot convert |
| F other / unclassified               | 1272| 552 | mixed; needs manual triage (some rating, some junk) |

## Caveats (read before using)
1. **Batch files ≠ experiments.** 908 A-class CSVs collapse to ~307 experiments; we output one
   norm per experiment folder. A folder occasionally mixes sub-experiments; ratings are still
   aggregated only from `Answer.Rating*` columns.
2. **Instructions are weaker than surveyor's.** MTurk does NOT store the question text or scale in
   the data (they lived in the HIT template). So the prompt here is a generic question inferred
   from the folder name (naturalness/acceptability/…) and the scale is inferred from observed
   response range. Treat instructions as approximate; verify before publishing.
3. **Unit numbering alignment is assumed** where the Rating index set exactly matches the stimulus
   index set. The 11 `_needs_review` experiments failed a sanity check (units looked like questions).
4. **No participant exclusions / attention-check filtering** applied.
5. **Not de-identified.** Raw MTurk CSVs contain WorkerId; folder names contain researcher names.
   Scrub before any release. (Only aggregated units+ratings were written out here, no WorkerId.)
6. **Dates 2011–2021, no manifest** — experiments are not linked to publications.
