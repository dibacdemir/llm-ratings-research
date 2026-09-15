"""Read the model's probability of each rating option from its logits.

No sampling, no parsing of generated text: we take the distribution over the
next token(s) directly, restrict it to the option strings ("1".."7"), and
renormalise. One forward pass per batch when the options are single tokens
(the usual case), otherwise one pass per option variant.
"""

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

DTYPES = {
    "bfloat16": torch.bfloat16,
    "float16": torch.float16,
    "float32": torch.float32,
    "auto": "auto",
}


def _logsumexp(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return float("-inf")
    m = max(vals)
    if m == float("-inf"):
        return m
    return m + float(np.log(sum(np.exp(v - m) for v in vals)))


class HFRatingScorer:
    """Scores a batch of prompts against a fixed list of option strings."""

    def __init__(
        self,
        model_name,
        dtype="bfloat16",
        device_map="auto",
        trust_remote_code=False,
        attn_implementation=None,
    ):
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name, trust_remote_code=trust_remote_code
        )
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "left"
        kwargs = {
            "dtype": DTYPES.get(dtype, dtype),
            "trust_remote_code": trust_remote_code,
        }
        if attn_implementation:
            kwargs["attn_implementation"] = attn_implementation
        if device_map:
            kwargs["device_map"] = device_map
        self.model = AutoModelForCausalLM.from_pretrained(model_name, **kwargs)
        self.model.eval()
        self.device = next(self.model.parameters()).device

    # -- option tokenisation -------------------------------------------------

    def variant_ids(self, options, with_leading_space=True, prefer_single_token=True):
        """Per option, the token-id sequences of its surface forms.

        "1" and " 1" can be different tokens, and which one carries the mass
        depends on the tokenizer and the chat template, so both are scored and
        their probabilities added. With `prefer_single_token` (the default) a
        variant is dropped when the same option also has a single-token form:
        for BPE vocabularies " 1" is [space, "1"], i.e. a *two*-token event that
        a chat template never emits, and keeping it would force the slow
        multi-pass path for nothing. Sentencepiece models, where "▁1" is the
        natural single token, keep working because the pruning is per option.
        """
        out = []
        for opt in options:
            surfaces = [str(opt)]
            if with_leading_space:
                surfaces.append(" " + str(opt))
            seqs, seen = [], set()
            for s in surfaces:
                ids = tuple(self.tokenizer.encode(s, add_special_tokens=False))
                if ids and ids not in seen:
                    seen.add(ids)
                    seqs.append(list(ids))
            if not seqs:
                raise ValueError("option %r tokenises to nothing" % (opt,))
            if prefer_single_token:
                singles = [s for s in seqs if len(s) == 1]
                if singles:
                    seqs = singles
            out.append(seqs)
        return out

    # -- scoring -------------------------------------------------------------

    @torch.inference_mode()
    def option_logprobs(self, texts, options, with_leading_space=True):
        """(len(texts), len(options)) array of unnormalised log P(option | text)."""
        variants = self.variant_ids(options, with_leading_space)
        single = all(len(seq) == 1 for opt in variants for seq in opt)
        if single:
            return self._single_token(texts, variants)
        return self._multi_token(texts, variants)

    def _encode(self, texts):
        enc = self.tokenizer(texts, return_tensors="pt", padding=True,
                             add_special_tokens=False)
        return {k: v.to(self.device) for k, v in enc.items()}

    def _forward_last(self, enc):
        """Logits for the final position only.

        By default a causal LM materialises logits at every position, which for
        a 262k-vocab model and a 700-token prompt is gigabytes of tensor we
        immediately discard — enough to OOM an 80 GB card on gemma-3-27b.
        `logits_to_keep=1` computes just the position we read.
        """
        try:
            return self.model(**enc, logits_to_keep=1).logits[:, -1, :].float()
        except TypeError:
            return self.model(**enc).logits[:, -1, :].float()

    def _single_token(self, texts, variants):
        enc = self._encode(texts)
        logits = self._forward_last(enc)
        logprobs = torch.log_softmax(logits, dim=-1).cpu().numpy()
        out = np.empty((len(texts), len(variants)), dtype=np.float64)
        for k, seqs in enumerate(variants):
            for b in range(len(texts)):
                out[b, k] = _logsumexp([logprobs[b, s[0]] for s in seqs])
        return out

    def _multi_token(self, texts, variants):
        """Fallback: sum the token logprobs of each option continuation."""
        enc = self._encode(texts)
        base_ids, base_mask = enc["input_ids"], enc["attention_mask"]
        b = base_ids.shape[0]
        per_variant = {}
        for k, seqs in enumerate(variants):
            for j, seq in enumerate(seqs):
                cont = torch.tensor(seq, device=self.device).unsqueeze(0).expand(b, -1)
                ids = torch.cat([base_ids, cont], dim=1)
                mask = torch.cat([base_mask, torch.ones_like(cont)], dim=1)
                # only the positions that predict the continuation are read, so
                # ask for just those: full-sequence logits (seq x vocab x batch)
                # are what OOMed Qwen2.5-32B on long 1-10 prompts
                logits = self.model(input_ids=ids, attention_mask=mask,
                                    logits_to_keep=len(seq) + 1).logits.float()
                lp = torch.log_softmax(logits[:, -(len(seq) + 1) : -1, :], dim=-1)
                tok = lp.gather(2, cont.unsqueeze(-1)).squeeze(-1).sum(dim=1)
                per_variant[(k, j)] = tok.cpu().numpy()
        out = np.empty((b, len(variants)), dtype=np.float64)
        for k, seqs in enumerate(variants):
            for i in range(b):
                out[i, k] = _logsumexp(
                    [float(per_variant[(k, j)][i]) for j in range(len(seqs))]
                )
        return out


def normalise(logprobs):
    """Log-probs over options -> (renormalised PMF, mass the options hold).

    ``option_mass`` is the total probability the model put on the valid answers
    before renormalising; a low value means the model wanted to say something
    else entirely and the PMF should not be trusted.
    """
    lp = np.asarray(logprobs, dtype=np.float64)
    mass = np.exp(lp).sum(axis=-1)
    m = lp.max(axis=-1, keepdims=True)
    w = np.exp(lp - m)
    pmf = w / w.sum(axis=-1, keepdims=True)
    return pmf, mass


def expected_rating(pmf, values):
    return float(np.dot(np.asarray(pmf, dtype=np.float64), np.asarray(values, float)))
