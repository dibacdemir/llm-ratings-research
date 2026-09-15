# Presentation — data descriptives & figures

Materials for the **Data** section of the summer presentation. Everything here is generated
from the repo by the two scripts below; no numbers are hand-entered.

- `build_catalog.py` → `dataset_catalog.csv` — one row per rating task with its linguistic
  domain, item count, rating count, and split-half reliability.
- `make_figures.py` → the three figures (PNG at 300 dpi for slides + PDF vector).

Re-run: `python3 presentation/build_catalog.py && python3 presentation/make_figures.py`

## Headline numbers (for the descriptives slide)

> **335 rating tasks**, spanning **6 levels of linguistic analysis**,
> covering **≈ 871,000 items** (unique words / sentences × property) and
> **≈ 19.4 million individual human ratings.**
> Human data is highly reliable: median split-half **r = 0.90** (291 tasks with individual responses).

**Composition**

| source | tasks | items | individual ratings |
|---|--:|--:|--:|
| Published norm studies (20 studies) | 64 | 802,536 | 17,305,294 |
| TedLab surveyor (new) | 100 | 13,777 | 333,190 |
| TedLab MTurk (new) | 171 | 54,498 | 1,722,570 |
| **total** | **335** | **870,811** | **19,361,054** |

All per-item instructions were manually adapted / reconstructed to be suitable for LLM prompting
(one instruction file per task in each `*/instructions/` folder).

## Figures

- **`figure1_composite.*`** — the main Nature-style figure: one multi-panel composite
  (panel **a** coverage, **b** composition, **c** reliability) with a "Figure 1 |" banner and
  panel letters. Use this as the anchor Data slide.

Standalone panels (for showing one at a time on separate slides):

- **`fig_examples.*`** — one real example per domain (high vs. low, with the human mean) + the actual LLM prompt; the "what does a task look like" slide.

- **`fig1_coverage.*`** — the key slide. One bar per task (n = 335), height = number of items
  (log scale), grouped and colored by linguistic domain, with a bracket over the three "Lexical"
  (word-meaning) sub-domains. Shows the coverage *and* the trade-off: syntax has many tasks with
  few items each; perceptual/motor has few tasks with huge item counts.
- **`fig2_reliability.*`** — split-half reliability (Spearman–Brown corrected) per task, by domain,
  for the 291 tasks with item-level individual ratings. Median line per domain + overall median.
- **`fig3_domains.*`** — composition summary: tasks per domain and items per domain (log).

## Domain taxonomy

Six domains (Level 1), with sub-domains (Level 2) in the catalog:

1. **Form (sub-lexical)** — orthography–phonology, iconicity, pseudowords
2. **Lexical: affective** — valence, arousal, dominance, emotion, motivation, …
3. **Lexical: perceptual / motor** — sensorimotor (11 Lancaster dims, Troche), imageability, concreteness, size
4. **Lexical: conceptual** — age of acquisition, frequency, familiarity, social, gender, semantic categories
5. **Syntax** — grammaticality, acceptability, naturalness (most of the new surveyor/MTurk data)
6. **Sentence semantics** — plausibility, predictability, coherence, discourse, sensibility

## Caveats (so the numbers are defensible)

- **Domain assignment is heuristic** (keyword rules on task/property names + prompts), reviewed by
  hand but not authoritative — a couple of tasks are judgment calls. Rules live in `build_catalog.py`;
  edit and re-run to reclassify. Happy to align the taxonomy with Andrea's preferred hierarchy.
- **Reliability = item-level split-half**, Spearman–Brown corrected: for each item the raters are
  randomly split in two, the two half-means are correlated across items. Computed only where
  `individual_ratings` exist (291/335 tasks); large datasets sampled to 6,000 items for speed.
- **Item counts** are unique units per task; the same word can appear across many tasks (e.g. the
  ~40k Lancaster words rated on 11 dimensions), so items are *not* unique word types overall.
- Published totals are dominated by a few very large norms (Lancaster, Muraki, Brysbaert), which is
  why "items per domain" is log-scaled.
