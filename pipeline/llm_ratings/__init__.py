"""Infrastructure for evaluating LLM ratings against human norms in this repo.

    data.py       find / load a task's CSV + instruction file, resolve its scale
    prompt.py     fill the <<{...}>> placeholder, apply the chat template
    hf_backend.py read P(option) straight off the logits (the expected-rating step)
    dist.py       Ted's W1 / equivalence / alignment code + helpers
"""

from . import data, dist, prompt  # noqa: F401

__all__ = ["data", "dist", "prompt"]
