Kuperman et al. (2012) age-of-acquisition (AoA) data.

File: kuperman2012_age_of_acquisition.csv

Scale: NOT a Likert rating. Values are estimated ages in years at which the
participant first understood the word (receptive AoA). Participants typed a
numeric age in years; "x" was used to mark an unknown word and was excluded
from item-level means.

Observed range in this file: 1.58 to 25.00 (mean of per-participant ages).
Theoretical range: 0+ (no upper bound was imposed; in practice ratings
saturate in the early adult years).

Implication for LLM prompting: do NOT instruct the model with a Likert scale
phrase. Ask for an age in years and let the model return an integer or
decimal number.
