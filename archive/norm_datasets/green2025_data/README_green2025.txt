Green et al. (2025) age-of-acquisition (AoA) data for reading and writing.

Files:
- green2025_aoa_reading.csv: estimated age at which the
  participant could first read (understand in print) the word.
- green2025_aoa_writing.csv: estimated age at which the
  participant could first spell the word correctly.

Scale: NOT a Likert rating. Values are ages in years, collected via a 0-20
slider. Participants could mark a word "Not applicable" instead of giving an
age; those responses are excluded from item-level means.

Observed range:
- Reading: 4.19 to 12.55 (mean of per-participant ages)
- Writing: 4.49 to 12.58

Implication for LLM prompting: ask for a number between 0 and 20, not for a
Likert digit. The instruction files already use the phrasing
"Respond with a number between 0 and 20", which is appropriate.
