Winter et al. (2017) iconicity data.

File: winter2017_iconicity.csv

Scale: -5 to +5 centered scale, NOT a 1-7 Likert scale.
  -5 = the word sounds like the OPPOSITE of what it means (anti-iconic).
   0 = arbitrary (no resemblance between form and meaning).
  +5 = the word sounds strongly like what it means (highly iconic).

This signed scale is required by the task: the instructions discuss words
that "sound like the opposite of what they mean" (e.g., MICROORGANISM being
a phonologically large word for something very small) alongside iconic and
arbitrary words. Only a centered scale can distinguish anti-iconic items
from purely arbitrary ones.

Observed range in this file: -2.80 to 4.47 (mean across raters per word),
with 575 of 3,002 items having negative means. Mean of means is approx 0.92.

KNOWN DISCREPANCY: the bundled instruction file
(winter2017_iconicity_i.txt) says "Please rate the word ... on a scale from
1 to 7." This does NOT match the data. The instruction should be revised to
say "from -5 to +5" before being used as an LLM prompt, otherwise the LLM
ratings will not be comparable to the human norms.

NB: This is distinct from the Winter et al. (2024) iconicity norms
(winter2024_iconicity.csv), which DO use a 1-7 scale.
