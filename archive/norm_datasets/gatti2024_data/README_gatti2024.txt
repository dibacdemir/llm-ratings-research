Gatti et al. (2024) pseudoword valence data.

Files:
- gatti2024_pseudoword_valence_intuitive.csv: 1,500 pseudowords from Experiment 2.
- gatti2024_pseudoword_valence_semantic_task.csv: 500 pseudowords from Experiment 3.

Columns:
- pseudoword: item being rated.
- mean: authors' continuous best-worst-derived valence score (higher = more positive); not a Likert mean.
- n: number of best-worst observations per item (30).

Notes: std and individual_ratings are omitted because the released RData used here does not include item-level SDs or raw participant-level ratings. Experiment 1 used existing Warriner et al. (2013) real-word 1-9 valence norms and is not duplicated here.

Elicitation note (2026-08-21): the HUMAN data were collected with a BEST-WORST
paradigm (each trial showed six pseudowords; participants picked the most positive
and most negative; the `mean` column is the authors' best-worst-derived valence
score in ~[0,1], higher = more positive — not a Likert mean). The instruction files
in instructions/gatti2024_instructions/ instead elicit a single-item 1-9 valence
rating (Warriner-style, which the original study builds on), because per-trial
six-item groupings are not in the released data and a six-alternative choice cannot
be reconstructed. LLM-human comparison for this dataset is therefore means-level
across DIFFERENT elicitation paradigms (single-item rating vs. best-worst score);
treat correlations accordingly. The two files keep the experiments' original
orientation: _intuitive = immediate first-reaction judgment (Experiment 2),
_semantic_task = judge the valence of the word's possible meaning (Experiment 3).
