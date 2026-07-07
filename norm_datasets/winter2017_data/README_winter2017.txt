Winter et al. (2017) iconicity data.

File: winter2017_iconicity.csv

Scale: 1 to 10 transformed scale, converted from the original -5 to +5 centered scale.

Transformation applied:
  new_score = 1 + ((old_score + 5) / 10) * 9
            = 0.9 * old_score + 5.5

Scale anchors after transformation:
   1 = the word sounds like the OPPOSITE of what it means (anti-iconic).
  5.5 = arbitrary (no resemblance between form and meaning).
  10 = the word sounds strongly like what it means (highly iconic).

The transformation preserves the ordering and distances of the original signed
scale while expressing values on a 1-to-10 scale. Values below 5.5 correspond
to originally negative/anti-iconic mean ratings; values above 5.5 correspond
to originally positive/iconic mean ratings.

The `mean` column was transformed with the formula above. If standard deviations
are present, they should be multiplied by 0.9 because affine rescaling changes
spread by the multiplicative factor only; this file has blank `std` values.
The `n` column is unchanged. The `individual_ratings` column is blank in this
file, so no trial-level responses were transformed.

Original observed range: -2.80 to 4.47 (mean across raters per word).
Transformed observed range in this file: 2.98 to 9.52.
Items below the transformed midpoint of 5.5: 575 of 3002.
Mean of transformed means is approx 6.32.
