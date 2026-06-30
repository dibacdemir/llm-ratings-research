import pandas as pd

"""
Process Lancaster Sensorimotor Norms (Lynott, Connell, Brysbaert, Brand & Carney, 2020)
into standardized per-dimension CSVs.

Inputs:
    1. Individual_participant_ratings_all_items_sensorimotor_norms_for_39954_words.UPDATED
       (long-format trial-level data: one row per participant rating)
    2. Lancaster_sensorimotor_norms_for_39707_words
       (wide-format aggregate file with means/SDs per dimension)

Output:
    One CSV per dimension named lancaster2020_<dimension>.csv with columns:
        word, mean, std, n, individual_ratings

Usage:
    Place both input files in the same directory as this script (or update the
    paths below), then run:  python process_lancaster.py

Notes:
    - Lancaster norms cover 11 dimensions: 6 perceptual (Auditory, Gustatory,
      Haptic, Interoceptive, Olfactory, Visual) and 5 motor (Foot_leg,
      Hand_arm, Head, Mouth, Torso). All on a 0-5 scale.
    - mean/std/n are computed from the raw individual ratings (not copied from
      the aggregate file). Discrepancies vs the aggregate file are flagged.
    - Missing ratings (NaN) are skipped per the spec rather than zero-filled.
"""

import os
import sys
import pandas as pd
import numpy as np

# ----------------------------------------------------------------------------
# CONFIG — edit these paths if your files live elsewhere
# ----------------------------------------------------------------------------
_SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
INDIVIDUAL_PATH = os.path.join(_SCRIPT_DIR, "Individual_participant_ratings_all_items_sensorimotor_norms_for_39954_words.UPDATED")
AGGREGATE_PATH  = os.path.join(_SCRIPT_DIR, "Lancaster_sensorimotor_norms_for_39707_words")
OUTPUT_DIR      = _SCRIPT_DIR

# The 11 sensorimotor dimensions Lancaster reports.
# Keys are lowercase output-file labels; values are the column-name stems used
# in the source files (the aggregate file uses e.g. "Auditory.mean", and the
# individual-ratings file typically has a column per dimension).
DIMENSIONS = {
    "auditory":     "Auditory",
    "gustatory":    "Gustatory",
    "haptic":       "Haptic",
    "interoceptive":"Interoceptive",
    "olfactory":    "Olfactory",
    "visual":       "Visual",
    "foot_leg":     "Foot_leg",
    "hand_arm":     "Hand_arm",
    "head":         "Head",
    "mouth":        "Mouth",
    "torso":        "Torso",
}

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def smart_read(path):
    """Read a file regardless of whether it has .csv/.txt/.xlsx/no extension."""
    if not os.path.exists(path):
        # Try common extensions
        for ext in (".csv", ".txt", ".xlsx", ".tsv"):
            if os.path.exists(path + ext):
                path = path + ext
                break
        else:
            raise FileNotFoundError(f"Could not find: {path}")

    if path.endswith(".xlsx"):
        return pd.read_excel(path, keep_default_na=False, na_values=[""])

    # Try comma first, then tab
    for sep in (",", "\t"):
        try:
            df = pd.read_csv(
                path, sep=sep,
                keep_default_na=False, na_values=[""],
                low_memory=False,
            )
            if df.shape[1] > 1:
                return df
        except Exception:
            continue
    # Last resort: let pandas sniff
    return pd.read_csv(path, sep=None, engine="python",
                       keep_default_na=False, na_values=[""])


def find_column(df, candidates, required=True):
    """Find a column whose name matches one of the candidates (case-insensitive)."""
    lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    if required:
        raise KeyError(
            f"None of {candidates} found in columns: {list(df.columns)}"
        )
    return None


def list_to_bracketed_string(values):
    """Convert a list of floats to '[v1, v2, v3]' string, preserving precision."""
    return "[" + ", ".join(f"{v:g}" for v in values) + "]"


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    print("Loading individual-ratings file...")
    indiv = smart_read(INDIVIDUAL_PATH)
    print(f"  Shape: {indiv.shape}")
    print(f"  Columns: {list(indiv.columns)}")

    print("\nLoading aggregate file...")
    agg = smart_read(AGGREGATE_PATH)
    print(f"  Shape: {agg.shape}")
    print(f"  Columns (first 10): {list(agg.columns)[:10]}")

    # --- Identify the word column in the individual-ratings file ---
    word_col = find_column(indiv, ["Word", "word", "Item", "stimulus"])
    print(f"\nUsing '{word_col}' as the word column in individual ratings.")

    # The individual-ratings file is typically *long* with one row per
    # (participant, word) and a column per dimension (e.g. 'Auditory_mean'
    # OR a single 'rating' column with a 'dimension' column). We handle both.
    indiv_cols_lower = [c.lower() for c in indiv.columns]
    has_dimension_column = "dimension" in indiv_cols_lower or "modality" in indiv_cols_lower
    has_rating_column    = "rating" in indiv_cols_lower or "response" in indiv_cols_lower

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    summary_rows = []

    for out_name, dim_stem in DIMENSIONS.items():
        print(f"\n--- Processing {out_name} ---")

        # ---- Pull individual ratings for this dimension ----
        if has_dimension_column and has_rating_column:
            # Long-long format: filter rows by dimension, pull rating column
            dim_col_in_indiv = find_column(indiv, ["dimension", "modality"])
            rating_col       = find_column(indiv, ["rating", "response"])
            mask = indiv[dim_col_in_indiv].astype(str).str.lower() == dim_stem.lower()
            sub = indiv.loc[mask, [word_col, rating_col]].copy()
            sub = sub.rename(columns={word_col: "word", rating_col: "rating"})
        else:
            # Wide-ish format: one column per dimension. Try common naming patterns.
            candidates = [dim_stem, f"{dim_stem}_mean", f"{dim_stem}.mean",
                          f"{dim_stem}_rating", f"{dim_stem}_Rating"]
            rating_col = find_column(indiv, candidates, required=False)
            if rating_col is None:
                print(f"  [skip] no column found for {dim_stem} in individual file")
                continue
            sub = indiv[[word_col, rating_col]].copy()
            sub = sub.rename(columns={word_col: "word", rating_col: "rating"})

        # Coerce to numeric, drop NaN
        sub["rating"] = pd.to_numeric(sub["rating"], errors="coerce")
        before = len(sub)
        sub = sub.dropna(subset=["rating", "word"])
        sub = sub[sub["word"].astype(str).str.strip() != ""]
        dropped = before - len(sub)
        if dropped:
            print(f"  Dropped {dropped} rows with missing word or non-numeric rating.")

        # Group by word -> compute mean, std, n, list of ratings
        grouped = sub.groupby("word", sort=True)["rating"]
        out = pd.DataFrame({
            "word":               grouped.size().index,
            "mean":               grouped.mean().values,
            "std":                grouped.std(ddof=1).values,  # sample SD (matches Lancaster)
            "n":                  grouped.size().values,
            "individual_ratings": [list_to_bracketed_string(list(g)) for _, g in grouped],
        })

        # ---- Cross-check against the aggregate file (flag discrepancies) ----
        agg_word_col = find_column(agg, ["Word", "word"])
        agg_mean_col = find_column(agg, [f"{dim_stem}.mean", f"{dim_stem}_mean", f"{dim_stem}.M"], required=False)
        if agg_mean_col is not None:
            agg_lookup = dict(zip(agg[agg_word_col].astype(str), pd.to_numeric(agg[agg_mean_col], errors="coerce")))
            diffs = []
            for w, m in zip(out["word"], out["mean"]):
                ref = agg_lookup.get(str(w))
                if ref is not None and not pd.isna(ref) and abs(ref - m) > 0.05:
                    diffs.append((w, m, ref))
            if diffs:
                print(f"  ⚠ {len(diffs)} words differ from aggregate file by >0.05 (showing first 3): {diffs[:3]}")
            else:
                print("  ✓ Means match aggregate file (within 0.05 tolerance).")

        out_path = os.path.join(OUTPUT_DIR, f"lancaster2020_{out_name}.csv")
        out.to_csv(out_path, index=False)
        print(f"  Wrote {len(out)} rows -> {out_path}")
        summary_rows.append((out_name, len(out), out_path))

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)
    for name, n, path in summary_rows:
        print(f"  {name:20s}  {n:>6d} rows  {path}")


if __name__ == "__main__":
    main()