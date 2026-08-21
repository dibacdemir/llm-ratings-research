# Audit of the 20 published reference datasets (2026-08-21)

Full audit of `norm_datasets/` + `instructions/` (the published norms, excluding
`mturk_norms/` and `surveyor_norms/`). Method: three parallel auditors, each doing a
**100%-of-rows** numeric pass (not samples), instruction checks, and
pipeline-registry cross-checks; the one high-severity finding was re-verified by
hand. The audit itself changed no files; the approved fixes were applied the same
day — see "Fixes applied" at the end. Current state and open items:
[`README.md`](README.md).

## Headline

The published sets are in very good shape: **13 of 20 families fully clean**, zero
numeric errors in ~700k checked rows, and every file that carries trial-level
ratings uses **sample SD (ddof=1)** — the same convention now used in
`mturk_norms/`/`surveyor_norms/`, so the whole repo is consistent. The issues below
are almost all structural/bookkeeping.

## Findings by severity

### High

1. **`tuckute2024` — CSV quoting corruption, 4 rows × all 10 files (40 rows).**
   Sentences containing embedded double quotes (raw lines 954, 1140, 1188, 1236 in
   each file, e.g. `"I think it's overblown," he said.`) were written with broken
   quoting: the unit truncates at the quote and the true mean lands in the `std`
   column (`mean` becomes garbage/empty). pandas silently downcasts the whole
   `mean` column to `object` because of these rows. Verified by hand. **Fixable
   in-repo**: the malformed lines still contain the full sentence and the true
   mean; rewriting those 4 lines per file with proper CSV quoting repairs it.
2. **`devarda2023_predictability`** (known, re-confirmed): instruction needs
   `{sentence_fragment}` + `{word}`, but the CSV stores only the target word — 214
   units are duplicated because distinct (fragment, word) trials collapse onto the
   same key. The fragments exist nowhere in the repo. **Not fixable here**; already
   correctly `EXCLUDED` in the pipeline.

### Medium

3. **`edwards2024` — the name is directionally misleading.** The registry/task name
   says "transparency," but the instruction elicits *difficulty* (1 = very easy …
   6 = very difficult), so **high scores = LOW transparency**. Data and instruction
   are internally consistent; this only needs a documentation warning (and care in
   any correlation write-up).
4. **`troche2014` — filename pairing broken for 2 of 14 dimensions** (confirmed):
   `troche2014_morality.csv` ↔ `troche2014_moral_i.txt` and
   `troche2014_social_interaction.csv` ↔ `troche2014_social_i.txt`. Contents match;
   a rename on one side fixes it.
5. **`tuckute2024` ships mean-only, undocumented**: `std` and `n` are blank in all
   2,000 rows of every file (the 4 "populated" std values are the corruption in
   finding 1) and, unlike `winter2017`, no README explains it.
6. **`muraki2023`**: (a) 28 fully-empty placeholder rows (unit only — the wired
   pipeline skips them, but they're dead weight); (b) it is the **only wired
   dataset without "Answer with one digit."** — its instruction instead offers an
   "I don't know the meaning of this expression" escape hatch. Decide: source
   fidelity vs. alignment with the other wired sets.
7. **Registry documentation gaps** in `pipeline/experiments.py`: `kuperman2012`
   (continuous ages, same disqualifier as the excluded `green2025`) and `gatti2024`
   (best-worst 6-item trials — the `{items}` instruction cannot be filled from the
   one-word-per-row CSV; groupings unreconstructible) are silently absent from both
   `DATASETS` and `EXCLUDED`; so are the aggregate-only `brysbaert2014` and
   `corenblum2025`. One-line `EXCLUDED` entries would make the omissions
   deliberate and reproducible.

### Low

8. Stale READMEs cite filenames that no longer exist: `README_gatti2024.txt`,
   `README_green2025.txt`.
9. `warriner2013_data/full_data/` is an unreferenced duplicate of the 3 main CSVs
   whose only difference is a bug: the word "null" became an empty string (a tool
   treated the string as NaN). Delete or fix.
10. `winter2017`: one duplicate unit ("down" twice, means 7.22 vs 4.81 — likely two
    senses collapsed); its 1–10 scale means "10" is not single-digit-safe if it is
    ever wired into the pipeline; instruction says "Answer with one number" (also
    `winter2024`, and `amouyal2024` says "one digit only") — minor style spread.

## Clean bills of health

`amouyal2024`, `brysbaert2014` (row count exactly matches the published norm),
`corenblum2025`, `dentella2023` (0/1 derivation documented and verified),
`diveica2023`, `giurgea2025`, all 11 `lancaster2020` tasks (identical 39,954-word
list across files, 0 out-of-range among ~440k values, instructions correctly state
the 0 minimum), `green2025` (exclusion reason re-confirmed), `pexman2019`,
`scott2018` (the mixed 1–7 / 1–9 scales match the published Glasgow Norms design —
verified correct, not an error), `warriner2013` (main files; the n≈900 anchor words
are the known calibration items), `winter2024`. `kuperman2012` is numerically clean
(the 19 n=0 and 59 n=1 rows with blank stats are legitimate).

## Registry verification

All 17 wired datasets' `lo`/`hi`/`placeholder` match both data ranges and
instructions exactly. All 3 `EXCLUDED` reasons re-confirmed accurate.

## Fixes applied 2026-08-21 (per Andrea's decisions)

1. **tuckute2024**: the 40 corrupted rows repaired in place (means recovered
   exactly; sentence text preserves all source characters — quote placement in the
   4 sentences is reconstructed, caveat documented in the new
   `README_tuckute2024.txt`, which also documents the mean-only format).
2. **troche2014**: instruction files renamed to match the CSVs
   (`moral_i.txt`→`morality_i.txt`, `social_i.txt`→`social_interaction_i.txt`).
3. **muraki2023**: 28 empty placeholder rows dropped (66,432→66,404); instruction's
   "I don't know the meaning" escape option replaced with the standard
   "Answer with one digit."
4. **warriner2013**: unused `full_data/` duplicate deleted; stale filenames in
   `README_gatti2024.txt` / `README_green2025.txt` corrected.

**Not fixed, by decision:** edwards2024 (left exactly as is); the registry — Andrea
clarified that aggregate-only data (brysbaert2014, corenblum2025, tuckute2024…) and
continuous scales (kuperman2012, green2025) are perfectly valid rating norms for
means-level comparison; "excluded" framing applies only to the trial-level
distribution pipeline and no registry edits were wanted. gatti2024 was
subsequently resolved (2026-08-21, Andrea's decision): the `{items}` best-worst
instructions were rewritten as single-item 1-9 valence ratings (`{word}`;
first-reaction wording for _intuitive, meaning-based wording for _semantic_task),
and README_gatti2024.txt documents that humans did best-worst — a cross-paradigm
means-level comparison. winter2017's
duplicate "down" and "one number" wording stay documented, unchanged.
