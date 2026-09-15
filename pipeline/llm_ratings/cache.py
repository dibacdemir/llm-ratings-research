"""Is a model's *complete* set of weights in the current HF cache?

Checking that `model.safetensors.index.json` resolves is not enough: a cache can
hold the index and none of the shards it points to, which then fails only after
a GPU has been allocated and the model starts loading. This walks the index.

    python -m llm_ratings.cache <model>          # exit 0 if usable
    python -m llm_ratings.cache <model> --where  # print the cache that has it
"""

import json
import os
import sys


def has_weights(model):
    """True if every weight file the model needs is present in the cache."""
    if os.path.isdir(model):
        return True
    from huggingface_hub import try_to_load_from_cache

    def cached(name):
        p = try_to_load_from_cache(model, name)
        return p if isinstance(p, str) and os.path.exists(p) else None

    if cached("model.safetensors"):
        return True
    idx = cached("model.safetensors.index.json")
    if idx:
        try:
            with open(idx) as fh:
                shards = set(json.load(fh)["weight_map"].values())
        except Exception:
            return False
        return bool(shards) and all(cached(s) for s in shards)
    if cached("pytorch_model.bin"):
        return True
    bin_idx = cached("pytorch_model.bin.index.json")
    if bin_idx:
        try:
            with open(bin_idx) as fh:
                shards = set(json.load(fh)["weight_map"].values())
        except Exception:
            return False
        return bool(shards) and all(cached(s) for s in shards)
    return False


def find_cache(model, caches):
    """The first cache in `caches` that holds all of `model`'s weights."""
    saved = os.environ.get("HF_HOME")
    try:
        for c in caches:
            os.environ["HF_HOME"] = c
            # huggingface_hub reads HF_HOME at import time, so reload constants
            import huggingface_hub.constants as K
            import importlib

            importlib.reload(K)
            import huggingface_hub.file_download as F

            importlib.reload(F)
            if has_weights(model):
                return c
    finally:
        if saved is None:
            os.environ.pop("HF_HOME", None)
        else:
            os.environ["HF_HOME"] = saved
    return None


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit("usage: python -m llm_ratings.cache <model> [--where]")
    m = args[0]
    if "--where" in sys.argv:
        caches = os.environ.get(
            "LLM_RATINGS_CACHES",
            "/home/phan3/orcd/scratch/huggingface "
            "/orcd/data/evelina9/001/USERS/phan3/hf_cache",
        ).split()
        hit = find_cache(m, caches)
        if hit:
            print(hit)
            sys.exit(0)
        sys.exit(1)
    sys.exit(0 if has_weights(m) else 1)
