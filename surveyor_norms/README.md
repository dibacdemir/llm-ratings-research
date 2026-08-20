# surveyor_norms — sentence-rating data converted from the TedLab surveyor export

Converted from `raw-data/surveyor_export.zip` (2026-07-15), then **repaired on
2026-08-20** following the audit in
[`../audit/DATA_AUDIT_2026-08-19.md`](../audit/DATA_AUDIT_2026-08-19.md).

## What's here

- `norm_datasets/{syntax,sentence_semantics}/<survey>.csv` — one file per survey,
  columns `unit, mean, std, n, individual_ratings, item_type`
  (`std` = **sample SD, ddof=1**; `item_type` ∈ `test` / `filler`, derived from the
  raw stimuli metadata — **fillers are included, marked, and left to the analyst**).
- `instructions/{syntax,sentence_semantics}/<survey>_i.txt` — the survey's own
  per-item question (verbatim from the raw `_stimuli.csv` `prompt` column) + the
  survey's own option labels on every scale point, **preserving the original digit
  mapping and direction** (e.g. `1 = Easy to understand … 5 = Hard to understand`
  stays reversed if the survey ran that way), "Answer with one digit.",
  `<<{sentence}>>`. Non-English surveys keep their own language.
- `a_index.csv` — one row per survey incl. `n_test`, `n_filler`, `anchors_dropped`,
  the scale labels, the prompt, and `language`.
- `non_english/` — the 10 non-English surveys, same layout
  (`norm_datasets/syntax/` + `instructions/syntax/`, instructions in the survey's
  own language): `chinese_dative` (Mandarin), `russian_freezing` (Russian),
  `dative_turkish` (Turkish), `dative_finnish` (Finnish), `italian_dative_v2` +
  `italian_locative_v7` (Italian), `european_portuguese_rc`/`_wh` (European
  Portuguese), `gabriel_rc`/`_wh` (Brazilian Portuguese). Kept apart so the main
  tree is uniformly English.

## Yield (post-repair)

**100 surveys** (2023–2026 Prolific, mostly 9.59 replications/extensions; 90 English in the main tree + 10 non-English in `non_english/`):
**13,695 units** (12,234 test + 1,461 filler), **330,886 individual ratings**.
Types: acceptability (54), acceptability_comprehensibility (5), other_rating (41).

## 2026-08-20 repair (summary)

1. **Biased practice/anchor items dropped** (82 units): each of the 41
   `discourse_*`/`coherence_*` surveys contained 2 anchor items whose response
   options embedded suggested answers ("…so you might rate them as a 4 or 5");
   human ratings for those were instruction-biased, so they were removed.
2. **`item_type` column added** (`test`/`filler` from raw metadata). The raw export
   never labels practice items, so no `practice` value occurs.
3. **Mac-Roman encoding repaired**: raw stimulus bytes (e.g. `0x8e` = "é") had been
   stripped, producing non-words like "stylish dcor" in 14 datasets; units now read
   "décor" as participants saw them.
4. **`std` recomputed as sample SD (ddof=1)** (was undocumented ddof=0).
5. **All 100 instructions rebuilt verbatim** from the raw per-item prompts and
   option labels (previously heterogeneous formatting, some with unlabeled or
   direction-ambiguous scales).

All kept units' rating multisets are byte-verified identical to the pre-repair
conversion (which itself was verified exact against raw); only the changes above
were applied.

## Caveats

1. **Per-sentence n is often small** (Latin-square designs) — check
   `median_n_per_unit`.
2. **No participant exclusions applied**; notably `class_demo`, `demo_9_59_2025`,
   `demo_9_59_2026` retain 30–45% self-reported non-native English speakers —
   consider a sensitivity analysis.
3. **Fillers are included** (marked in `item_type`) — filter as your analysis
   requires.
4. **Not de-identified**: `a_index.csv` retains creator emails. Scrub before release.
5. Some 9.59 replications may overlap conceptually with the 20 published datasets in
   the repo root — check before pooling.
