#!/usr/bin/env python
"""Pilot of Andrea's regression approach: predict human ratings from a model's
hidden states with ridge regression, instead of asking the model for a number.

For each item the model reads only

    Consider this linguistic input '<item>'.

and the hidden state of every layer is averaged over the item's tokens. Per
task, N items are drawn at random; 15% are held out as test, the rest is split
75/10 (of the full N) into train and dev. For every layer a ridge model is
fitted on train with 5-fold CV over alpha in logspace(-5, 4, 10); the layer with
the best dev Pearson wins; a final model with that layer and alpha is refitted
on train+dev and scored on test (Pearson). Repeated --resamples times with
different draws and averaged. Features are scaled by their std (no centring).

Ridge is solved in the dual (n x n) with numpy, equivalent to RidgeCV for n < d.

    python pipeline/regress_pilot.py --model Qwen/Qwen2.5-7B-Instruct \
        --tasks amouyal2024_plausibility,diveica2023_socialness --n 300 --resamples 10
"""

import argparse
import csv
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_ratings import data  # noqa: E402
from human_reliability import _pearson, _rank  # noqa: E402

TEMPLATE = "Consider this linguistic input '%s'."
ALPHAS = np.logspace(-5, 4, 10)


def embed(model_id, items, batch_size=16, max_pool=1200, seed=0):
    """-> (idx, H) with H[n_items, n_layers, dim] float32, mean over the item's tokens."""
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    tok = AutoTokenizer.from_pretrained(model_id)
    tok.padding_side = "right"
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_id, dtype=torch.bfloat16, device_map="auto").eval()
    rng = np.random.default_rng(seed)
    idx = np.arange(len(items)) if len(items) <= max_pool else np.sort(rng.choice(len(items), max_pool, replace=False))
    units = [items[i]["unit"] for i in idx]
    H = None
    for b in range(0, len(units), batch_size):
        texts = [TEMPLATE % u for u in units[b:b + batch_size]]
        enc = tok(texts, return_tensors="pt", padding=True, return_offsets_mapping=True, add_special_tokens=True)
        offs = enc.pop("offset_mapping").numpy()
        with torch.inference_mode():
            out = model(**{k: v.to(model.device) for k, v in enc.items()}, output_hidden_states=True)
        hs = torch.stack(out.hidden_states, 1)        # [B, L, T, D]
        for j, (u, text) in enumerate(zip(units[b:b + batch_size], texts)):
            s = text.index("'") + 1
            e = s + len(u)
            span = [t for t, (a, z) in enumerate(offs[j]) if z > a and a < e and z > s]
            if not span:
                span = [int(enc["attention_mask"][j].sum()) - 1]
            v = hs[j, :, span, :].float().mean(1).cpu().numpy().astype(np.float32)
            if H is None:
                H = np.zeros((len(units), v.shape[0], v.shape[1]), np.float32)
            H[b + j] = v
    return idx, H


def _ridge_dual(Xtr, ytr, Xte, alphas):
    """Ridge in the dual (n x n), with intercept, for every alpha at once.
    n <= 300 here, so this is a few small solves instead of sklearn's CV loop."""
    mu = ytr.mean()
    K = Xtr @ Xtr.T
    Kte = Xte @ Xtr.T
    n = len(ytr)
    out = []
    w, V = np.linalg.eigh(K)
    Vy = V.T @ (ytr - mu)
    for a in alphas:
        coef = V @ (Vy / (w + a))               # (K + aI)^-1 (y - mu)
        out.append(Kte @ coef + mu)
    return np.stack(out)                        # [n_alpha, n_te]


def fit_task(H, y, n, resamples, seed=0):
    rng = np.random.default_rng(seed)
    L = H.shape[1]
    dev_curves, tests, layers, alphas = [], [], [], []
    for r in range(resamples):
        pick = rng.choice(len(y), n, replace=False)
        rng.shuffle(pick)
        n_te, n_dev = int(round(0.15 * n)), int(round(0.10 * n))
        te, dev, tr = pick[:n_te], pick[n_te:n_te + n_dev], pick[n_te + n_dev:]
        folds = np.array_split(np.arange(len(tr)), 5)
        dev_r = np.full(L, np.nan)
        best = (-np.inf, None, None)
        for l in range(L):
            X = H[:, l, :].astype(np.float32)
            sd = X[tr].std(0) + 1e-6
            X = X / sd                              # variance-only scaling, fitted on train
            # 5-fold CV on train to pick alpha
            cv = np.zeros(len(ALPHAS))
            for f in folds:
                m = np.ones(len(tr), bool); m[f] = False
                P = _ridge_dual(X[tr[m]], y[tr[m]], X[tr[f]], ALPHAS)
                cv += [_pearson(P[i], y[tr[f]]) for i in range(len(ALPHAS))]
            ai = int(np.nanargmax(cv))
            P = _ridge_dual(X[tr], y[tr], X[dev], [ALPHAS[ai]])
            dev_r[l] = _pearson(P[0], y[dev])
            if dev_r[l] > best[0]:
                best = (dev_r[l], l, ALPHAS[ai])
        l, a = best[1], best[2]
        X = H[:, l, :].astype(np.float32)
        trdev = np.concatenate([tr, dev])
        X = X / (X[trdev].std(0) + 1e-6)
        P = _ridge_dual(X[trdev], y[trdev], X[te], [a])
        tests.append(_pearson(P[0], y[te])); layers.append(l); alphas.append(a); dev_curves.append(dev_r)
    return {"test_r_mean": float(np.mean(tests)), "test_r_sd": float(np.std(tests)),
            "test_r_all": [round(float(x), 3) for x in tests],
            "best_layer_median": int(np.median(layers)), "best_layers": layers,
            "alpha_median": float(np.median(alphas)),
            "dev_curve": np.nanmean(np.array(dev_curves), 0).tolist()}


def ratings_reference(model_id, task):
    slug = model_id.split("/")[-1]
    f = os.path.join("result", slug, task + "__autofmt.jsonl")
    if not os.path.exists(f):
        return None
    R = [json.loads(l) for l in open(f)]
    e = np.array([r["expected"] for r in R]); h = np.array([r["human_mean"] for r in R])
    return {"pearson": _pearson(e, h), "spearman": _pearson(_rank(e), _rank(h)),
            "mass": float(np.median([r["option_mass"] for r in R]))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--n", default="300", help="comma-separated item counts to try")
    ap.add_argument("--resamples", type=int, default=10)
    ap.add_argument("--out", default="analysis/regress_pilot")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    ns = [int(x) for x in args.n.split(",")]
    slug = args.model.split("/")[-1]
    rows = []
    for task in args.tasks.split(","):
        t0 = time.time()
        loc = data.find_task(task)
        items = [it for it in data.load_items(loc["csv"]) if it.get("mean") is not None]
        idx, H = embed(args.model, items)
        y = np.array([float(items[i]["mean"]) for i in idx])
        ceil = (data.task_metadata(task).get("human_reliability") or {}).get("spearman_sb")
        ref = ratings_reference(args.model, task)
        print("\n== %s  (%d items pooled, %d layers x %d dims, %.0fs to embed) =="
              % (task, len(idx), H.shape[1], H.shape[2], time.time() - t0), flush=True)
        for n in ns:
            if n > len(idx):
                print("   N=%d: only %d items, skipped" % (n, len(idx))); continue
            res = fit_task(H, y, n, args.resamples)
            print("   N=%-4d test r = %.3f ± %.3f   best layer %2d/%d   alpha %.0e   | ratings: pearson %s  spearman %s  | human reliability %s"
                  % (n, res["test_r_mean"], res["test_r_sd"], res["best_layer_median"], H.shape[1] - 1, res["alpha_median"],
                     "%.3f" % ref["pearson"] if ref else "-", "%.3f" % ref["spearman"] if ref else "-",
                     "%.2f" % ceil if ceil else "-"), flush=True)
            rows.append({"model": slug, "task": task, "level": data.task_metadata(task).get("level"), "n": n,
                         "resamples": args.resamples, "test_r_mean": round(res["test_r_mean"], 4),
                         "test_r_sd": round(res["test_r_sd"], 4), "best_layer": res["best_layer_median"],
                         "n_layers": H.shape[1] - 1, "alpha": res["alpha_median"],
                         "ratings_pearson": round(ref["pearson"], 4) if ref else "",
                         "ratings_spearman": round(ref["spearman"], 4) if ref else "",
                         "ratings_mass": round(ref["mass"], 3) if ref else "",
                         "human_rho_sb": ceil or "", "dev_curve": json.dumps([round(x, 3) for x in res["dev_curve"]])})
        del H
        out = os.path.join(args.out, "%s.csv" % slug)
        with open(out, "w", newline="") as fh:      # rewritten after every task, so a timeout loses nothing
            w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n"); w.writeheader(); w.writerows(rows)
    print("\nwrote", out)


if __name__ == "__main__":
    main()
