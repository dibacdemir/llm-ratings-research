De Varda et al. (2024) cloze probability data.

File: devarda2023_cloze_probability.csv

Scale: NOT a Likert rating. Values are cloze probabilities in [0, 1],
computed per (sentence_fragment, target_word) item as the proportion of
participants who produced the target word as the next word in a free
continuation task. Individual responses are binary (1 = produced target,
0 = produced any other word); the mean across participants is the cloze
probability.

Observed range: 0.000 to 1.000, mean approx 0.20.

Implication for LLM prompting: this is not a rating task. To replicate the
human procedure with an LLM, prompt for a single next-word continuation
(as the corresponding instruction file does: "Write the next word of the
sentence ... Answer with one word") and compute item-level cloze
probabilities across many LLM samples or via token probabilities.

Related companion file: devarda2023_predictability.csv IS a Likert rating
(1-5) and follows the standard convention.
