# surveyor_norms — sentence-rating data converted from the TedLab surveyor export

Auto-converted from `surveyor_export.zip` (2026-07-15) into the same schema as the
existing `norm_datasets/` + `instructions/` in this repo. **Nothing in the original
repo was modified**; this is a standalone sibling directory.

## What's here
- `norm_datasets/<survey>.csv` — one file per survey, columns: `unit, mean, std, n, individual_ratings`
  (`unit` = the sentence/stimulus shown, HTML stripped to plain text)
- `instructions/<survey>_i.txt` — reconstructed prompt: the survey's own question + rating
  scale + `<<{sentence}>>` placeholder, mirroring the existing instruction format
- `a_index.csv` — one row per survey (type, participants, #units, #ratings, median n/unit, scale, prompt)
- `_needs_review/` — 15 surveys kept OUT of the main set (see caveats)

## Selection (of 345 surveys in the export)
Kept only surveys that were (a) numeric-rating (>90% of critical responses parse to a number),
(b) text-only (no `<audio>`/`<img>` stimuli), giving **100 clean surveys, 13,777 sentences,
333,190 individual ratings**. Types: acceptability (54), acceptability_comprehensibility (5),
other_rating (41).

Excluded by design (not convertible to a single numeric norm): noisy_channel_comprehension,
meaning_inference, completion, forced_choice, and all audio/image surveys.

## Caveats (read before using)
1. **Per-sentence n is often small.** Latin-square designs split ~30 participants across
   many conditions, so ~15 surveys have a median of <10 ratings per unique sentence
   (see `median_n_per_unit` in `a_index.csv`). Fine for item-level correlation, weak per item.
2. **Instructions are reconstructed** from the survey's per-item prompt + option labels, NOT
   the original full participant instructions (those weren't in the export). Usually one clean
   question ("How natural is the sentence?") + scale, but verify before publishing.
3. **`_needs_review/` = 15 post-experiment attitude questionnaires** (e.g. "I like the way a
   British accent sounds", Strongly Disagree–Agree). They convert numerically but are not
   linguistic-stimulus norms. Excluded from the main set; decide case by case.
4. **No participant exclusions applied.** All submitted responses are aggregated; no attention-
   check filtering or non-native-speaker removal was done here.
5. **Not de-identified.** `a_index.csv` retains the creator's email (survey provenance). Scrub
   before any public release.
6. **Mostly 9.59 course replications/extensions** — quality varies; some replicate studies that
   may already exist among the 20 published datasets in this repo (check for overlap/novelty).
