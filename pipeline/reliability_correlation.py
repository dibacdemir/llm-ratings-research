# Split-half reliability of the human norms, and model-human correlation
# corrected against that reliability ceiling.
#
# Reliability is only defined where we have trial-level human responses, so this
# script reuses the dataset registry in experiments.py, which lists exactly those.
#
# Usage:
#     python reliability_correlation.py --dataset diveica2023_socialness
#     python reliability_correlation.py --dataset all --results results/meta-llama_Llama-3.1-8B-Instruct

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.stats import norm, pearsonr, spearmanr

from experiments import DATASETS, load_items, resolve_datasets


def splithalf_reliability(data, n_iterations=100, seed=0, progress=True):
    '''Reliability with Spearman-Brown correction under n random splits of raters.

    data: list of per-item arrays of individual responses.
    '''
    data = [np.asarray(x, float) for x in data if len(x) > 2]
    if len(data) < 3:
        raise ValueError("need at least 3 items with >2 raters")

    rng = np.random.default_rng(seed)
    iterator = range(n_iterations)
    if progress:
        try:
            from tqdm import tqdm
            iterator = tqdm(iterator, desc="split-half")
        except ImportError:
            pass

    r = []
    for _ in iterator:
        a, b = [], []
        for item in data:
            n = len(item)
            idx_a = rng.choice(n, n // 2, replace=False)
            mask = np.ones(n, bool)
            mask[idx_a] = False
            a.append(item[idx_a].mean())
            b.append(item[mask].mean())
        r_iter, _ = pearsonr(a, b)
        r.append(r_iter)

    r = np.asarray(r)
    mean_r = float(r.mean())
    sd_r = float(r.std(ddof=1))
    ci = norm.interval(0.95, loc=mean_r, scale=sd_r / np.sqrt(len(r)))

    # Spearman-Brown corrected: r_sb = 2r / (1 + r)
    r_sb = 2 * r / (1 + r)
    mean_r_sb = float(r_sb.mean())
    sd_r_sb = float(r_sb.std(ddof=1))
    ci_sb = norm.interval(0.95, loc=mean_r_sb, scale=sd_r_sb / np.sqrt(len(r_sb)))

    print(f"R (uncorrected):      mean={mean_r:.4f}, SD={sd_r:.4f}, 95% CI=[{ci[0]:.4f}, {ci[1]:.4f}]")
    print(f"R (SB-corrected):     mean={mean_r_sb:.4f}, SD={sd_r_sb:.4f}, 95% CI=[{ci_sb[0]:.4f}, {ci_sb[1]:.4f}]")

    return {
        "r": mean_r, "sd": sd_r, "ci": [float(ci[0]), float(ci[1])],
        "r_corrected": mean_r_sb, "sd_corrected": sd_r_sb,
        "ci_corrected": [float(ci_sb[0]), float(ci_sb[1])],
        "n_items": len(data),
    }


def read_model_results(items_csv):
    '''Map unit -> model expected rating from an experiments.py items CSV.'''
    out = {}
    with open(items_csv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out[row["unit"]] = float(row["model_expected"])
    return out


def model_human_correlation(model_expected, human_means, reliability=None):
    model_expected = np.asarray(model_expected, float)
    human_means = np.asarray(human_means, float)
    r, p = pearsonr(model_expected, human_means)
    rho, p_rho = spearmanr(model_expected, human_means)
    out = {
        "n_items": int(len(model_expected)),
        "pearson_r": float(r), "pearson_p": float(p),
        "spearman_rho": float(rho), "spearman_p": float(p_rho),
    }
    if reliability and reliability > 0:
        # attenuation correction: how close the model gets to the human ceiling
        out["r_over_ceiling"] = float(r / np.sqrt(reliability))
    return out


def run_dataset(spec, args, results_dir):
    print(f"\n=== {spec.key} ===", flush=True)
    items, _ = load_items(spec, limit=args.limit)
    if len(items) < 3:
        print("  not enough usable items, skipping")
        return None

    rel = splithalf_reliability(
        [it.ratings for it in items],
        n_iterations=args.n_iterations,
        seed=args.seed,
        progress=not args.quiet,
    )
    summary = {"dataset": spec.key, "reliability": rel}

    if results_dir:
        items_csv = Path(results_dir) / f"{spec.key}_items.csv"
        if items_csv.exists():
            model_by_unit = read_model_results(items_csv)
            paired = [(model_by_unit[it.unit], it.human_mean)
                      for it in items if it.unit in model_by_unit]
            if len(paired) > 2:
                model_vals, human_vals = zip(*paired)
                corr = model_human_correlation(
                    model_vals, human_vals, reliability=rel["r_corrected"]
                )
                summary["model_vs_human"] = corr
                summary["model_results"] = str(items_csv)
                print(f"  model vs human: r={corr['pearson_r']:.4f}  "
                      f"rho={corr['spearman_rho']:.4f}  "
                      f"r/ceiling={corr.get('r_over_ceiling', float('nan')):.4f}  "
                      f"(n={corr['n_items']})")
            else:
                print(f"  {items_csv.name} has too few matching units")
        else:
            print(f"  no model results at {items_csv}, reliability only")
    return summary


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", default="all",
                   help="dataset key, comma-separated keys, a source prefix, or 'all'")
    p.add_argument("--results", help="directory of experiments.py items CSVs "
                                     "(e.g. results/<model_slug>)")
    p.add_argument("--output", default=None, help="path for the JSON summary")
    p.add_argument("--n-iterations", type=int, default=100)
    p.add_argument("--limit", type=int, help="cap items per dataset")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--quiet", action="store_true", help="no progress bars")
    p.add_argument("--list", action="store_true")
    args = p.parse_args(argv)

    if args.list:
        for key in DATASETS:
            print(key)
        return 0

    specs = resolve_datasets(args.dataset)
    summaries = [s for s in (run_dataset(spec, args, args.results) for spec in specs) if s]

    out_path = Path(args.output) if args.output else (
        Path(args.results) / "reliability.json" if args.results
        else Path("results") / "reliability.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print(f"\nwrote {len(summaries)} reliability summaries to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
