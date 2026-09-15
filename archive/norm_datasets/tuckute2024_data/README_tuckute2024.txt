Tuckute et al. (2024) sentence norms — 10 dimension files, 2,000 sentences each.

Format note (2026-08-21): these files are MEAN-ONLY. The source data used here did
not include item-level SDs, per-item n, or raw participant-level ratings, so the
std, n, and individual_ratings columns are empty by design in all rows.

Repair note (2026-08-21): 4 rows per file (the same 4 sentences in each of the 10
files) were corrupted by a CSV-quoting bug at conversion time — sentences containing
embedded double quotes were split at an internal comma, shifting the mean into the
std column. They were repaired in place: the numeric mean is recovered exactly, and
the sentence text preserves every character of the corrupted source with the comma
restored at the split point. Because the corruption garbled quote placement, the
exact positions of quotation marks in these 4 sentences are RECONSTRUCTED and may
differ from the original published materials (e.g. "...overblown," he said. vs
"...overblown", he said.). Cross-check against the published Tuckute et al. (2024)
materials if these specific items matter:
  1. "I think it's overblown, he said."
  2. Even June yells out, "Kaede, that-"""
  3. Items where Author is "Scott, Braden"""
  4. Items where Author is "Polgar, G."""
