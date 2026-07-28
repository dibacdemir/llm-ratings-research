# New Rating Datasets — Integration & Audit Report
_2026-07-20 · covers `surveyor_norms/` and `mturk_norms/` (original 20 datasets untouched)_

## Bottom line
**271 usable datasets · 68,275 units · 2,055,760 individual human ratings**, all numerically
re-verified from the raw source. 30 flagged datasets were excluded. Every file in both
raw dumps is classified and accounted for.

## 1. Usable data (checked, clean)
| folder | usable datasets | units | ratings | instructions |
|---|--:|--:|--:|---|
| `surveyor_norms/` (2023–2026, Prolific) | 100 | 13,777 | 333,190 | faithful (from survey data) |
| `mturk_norms/` (2011–2021, MTurk) | 171 | 54,498 | 1,722,570 | inferred |
| **total** | **271** | **68,275** | **2,055,760** | |

Schema matches the existing repo exactly: `unit, mean, std, n, individual_ratings` + one
`*_i.txt` instruction per dataset.

## 2. Verification — all passed
- **Self-consistency:** 0 problems / 70,971 rows (mean·std·n vs individual_ratings; no HTML, empty, or dup units).
- **Independent re-derivation from raw** (second implementation): surveyor exact; MTurk **0 mismatches** over 56,976 units / 1.78M ratings — stimulus↔rating alignment confirmed.
- **No data loss:** index rows = CSV files = instruction files, both sets.
- **Accounting closes:** surveyor 115 + 230 = 345; MTurk categories sum to exactly 2,853, each file once.
- **Scale/value sanity:** all integers on one clean scale (1–3/1–5/1–7); 0 out-of-range; every mean in range.
- **No wrongful inclusions:** 0 games/RT/external-only leaked in.

## 3. Fixes applied during the audit
- **Excluded 4 broken MTurk files**: 2 with image-filename units (`.png`), 1 all-boilerplate, 1 with n=1 for every unit.
- **Upgraded 108 MTurk instructions** to dimension-specific wording; fixed the 20 `massive_mem` word-norm sets that had shared one identical "Rate the sentence" line.
- **"Accent-stripping bug" → false alarm.** Converter preserves accents; stray `dcor` units come from raw data that lost the é upstream (faithful reproduction).

## 4. Not converted — classified & checked
**Surveyor (230 of 345):** non-numeric responses 189 · audio 34 · image 7.
**MTurk (2,853 files):** A rating→converted 908 · F other/unclassified 1,272 · C yes/no 343 ·
E surveycode-only (external) 178 · B rating/stimulus-unclear 113 · D memory-or-RT-game 39.
Full listing: `mturk_norms/_remaining_classification.csv`. D and E confirmed genuinely non-convertible.

## 5. Recoverable yield (future work, quantified)
- **~220 datasets** via a "proportion" encoding (like existing `dentella2023`): ~80 surveyor binary + ~140 MTurk yes/no.
- **~190 MTurk files** hidden in category F (non-standard column names): incl. 59 "X-by-Y" 0–100 slider norms, ~31-file gesture Likert series.
- **~65 surveyor** interleaved acceptability+comprehension surveys (split by sub-experiment → clean 1–7 norm).
- **3 surveys** blocked by an invisible U+200E prefix — one-line fix, quick win.

## 6. Caveats to raise
- MTurk instructions are **inferred, not original** (63/171 still generic; scale inferred from responses). Surveyor instructions are faithful.
- **Thin per-item n** in Latin-square designs (20 surveyor + ~16 MTurk median <10; 7 files flagged `caveat` in index).
- **Not de-identified** (researcher emails in provenance; WorkerIds in raw MTurk). Scrub before release.
- Mostly **9.59 course replications** — variable quality; check overlap with the 20 published datasets.

---
_Audit method: deterministic re-derivation from raw + a 24-agent adversarial review (17/18 major findings confirmed, 1 overstated). Per-folder READMEs and `a_index.csv` (with `quality_flag`) carry the details._
