# Models

The design, not a head count. Seven public model families, every size each
family offers, so that a comparison within a family isolates scale and a
comparison across families at one size isolates training recipe. Every model
is the instruction-tuned release; reasoning models whose thinking cannot be
switched off are excluded (the reading is the first answer token), hybrid
models run with thinking off.

Links go to the HuggingFace model page; ids were checked against the Hub on
2026-09-17. Status: ✓ run · ▶ queued · — not yet. `gated` needs access
approved on the model page. Weights are downloaded by the job and deleted
after a complete run (`pipeline/run_checked.sh`).

## 1. The main table: seven families × every size

Figure 1 of the paper: one line per family, scale on the x-axis, one panel per
level of language.

| family | model | params (B) | status | notes |
|---|---|--:|:-:|---|
| Qwen2.5 | [Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct) | 0.5 | ✓ | answers, but uncorrelated with raters |
| | [Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) | 1.5 | ✓ | |
| | [Qwen2.5-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct) | 3.1 | ✓ | |
| | [Qwen2.5-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) | 7.6 | ✓ | |
| | [Qwen2.5-14B-Instruct](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct) | 14.8 | ✓ | |
| | [Qwen2.5-32B-Instruct](https://huggingface.co/Qwen/Qwen2.5-32B-Instruct) | 32.8 | ✓ | |
| | [Qwen2.5-72B-Instruct](https://huggingface.co/Qwen/Qwen2.5-72B-Instruct) | 72.7 | — | needs 2 × A100; last |
| Qwen3 | [Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B) | 0.8 | ✓ | thinking off |
| | [Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B) | 2.0 | ✓ | thinking off |
| | [Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B) | 4.0 | ✓ | thinking off |
| | [Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B) | 8.2 | ✓ | thinking off |
| | [Qwen3-14B](https://huggingface.co/Qwen/Qwen3-14B) | 14.8 | ✓ | thinking off |
| | [Qwen3-32B](https://huggingface.co/Qwen/Qwen3-32B) | 32.8 | ✓ | thinking off |
| Llama 3 | [Llama-3.2-1B-Instruct](https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct) | 1.2 | ✓ | no digit on 278/285 tasks; gated |
| | [Llama-3.2-3B-Instruct](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct) | 3.2 | ✓ | gated |
| | [Meta-Llama-3.1-8B-Instruct](https://huggingface.co/meta-llama/Meta-Llama-3.1-8B-Instruct) | 8.0 | ✓ | gated |
| | [Llama-3.1-70B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-70B-Instruct) | 70.6 | — | needs 2 × A100; gated; last |
| Gemma 3 | [gemma-3-1b-it](https://huggingface.co/google/gemma-3-1b-it) | 1.0 | ✓ | answers, but uncorrelated with raters; gated |
| | [gemma-3-4b-it](https://huggingface.co/google/gemma-3-4b-it) | 4.3 | ✓ | gated |
| | [gemma-3-12b-it](https://huggingface.co/google/gemma-3-12b-it) | 12.2 | ✓ | gated |
| | [gemma-3-27b-it](https://huggingface.co/google/gemma-3-27b-it) | 27.4 | ✓ | gated |
| OLMo 2 | [OLMo-2-0425-1B-Instruct](https://huggingface.co/allenai/OLMo-2-0425-1B-Instruct) | 1.5 | ✓ | fully open training data |
| | [OLMo-2-1124-7B-Instruct](https://huggingface.co/allenai/OLMo-2-1124-7B-Instruct) | 7.3 | ✓ | |
| | [OLMo-2-1124-13B-Instruct](https://huggingface.co/allenai/OLMo-2-1124-13B-Instruct) | 13.7 | ✓ | |
| | [OLMo-2-0325-32B-Instruct](https://huggingface.co/allenai/OLMo-2-0325-32B-Instruct) | 32.2 | ✓ | |
| Yi 1.5 | [Yi-1.5-6B-Chat](https://huggingface.co/01-ai/Yi-1.5-6B-Chat) | 6.1 | ✓ | |
| | [Yi-1.5-9B-Chat](https://huggingface.co/01-ai/Yi-1.5-9B-Chat) | 8.8 | ✓ | |
| | [Yi-1.5-34B-Chat](https://huggingface.co/01-ai/Yi-1.5-34B-Chat) | 34.4 | ✓ | |
| Falcon 3 | [Falcon3-1B-Instruct](https://huggingface.co/tiiuae/Falcon3-1B-Instruct) | 1.7 | ✓ | |
| | [Falcon3-3B-Instruct](https://huggingface.co/tiiuae/Falcon3-3B-Instruct) | 3.2 | ▶ | |
| | [Falcon3-7B-Instruct](https://huggingface.co/tiiuae/Falcon3-7B-Instruct) | 7.5 | ✓ | |
| | [Falcon3-10B-Instruct](https://huggingface.co/tiiuae/Falcon3-10B-Instruct) | 10.3 | ✓ | |

Sizes do not line up across families, so the cross-family comparison at a fixed
size uses two windows every family has: 1–4B and 7–10B. Scale curves are
compared by shape, not point by point.

## 2. Generations: one company, one size, four years

Same size, same maker, different year. Which levels did a new generation
improve?

| model | params (B) | status | notes |
|---|--:|:-:|---|
| [Qwen1.5-7B-Chat](https://huggingface.co/Qwen/Qwen1.5-7B-Chat) | 7.7 | ✓ | 2024-02 |
| [Qwen2-7B-Instruct](https://huggingface.co/Qwen/Qwen2-7B-Instruct) | 7.6 | ✓ | 2024-06 |
| Qwen2.5-7B-Instruct | 7.6 | ✓ | 2024-09, in the main table |
| Qwen3-8B | 8.2 | ✓ | 2025-04, in the main table |

## 3. More families at 7–10B (second phase)

Widens the cross-family comparison from 7 families to ~20 at the one size
every family has. One GPU-hour each. Supplementary material.

| model | params (B) | status | notes |
|---|--:|:-:|---|
| [Ministral-8B-Instruct-2410](https://huggingface.co/mistralai/Ministral-8B-Instruct-2410) | 8.0 | ✓ | |
| [OLMo-3-7B-Instruct](https://huggingface.co/allenai/OLMo-3-7B-Instruct) | 7.3 | ✓ | |
| [Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B) | 9.7 | ✓ | |
| [Mistral-7B-Instruct-v0.3](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3) | 7.2 | — | |
| [phi-4](https://huggingface.co/microsoft/phi-4) | 14.7 | — | |
| [glm-4-9b-chat-hf](https://huggingface.co/THUDM/glm-4-9b-chat-hf) | 9.4 | — | |
| [internlm3-8b-instruct](https://huggingface.co/internlm/internlm3-8b-instruct) | 8.8 | — | custom code |
| [deepseek-llm-7b-chat](https://huggingface.co/deepseek-ai/deepseek-llm-7b-chat) | 7 | — | |
| [granite-3.3-8b-instruct](https://huggingface.co/ibm-granite/granite-3.3-8b-instruct) | 8.2 | — | |
| [EXAONE-3.5-7.8B-Instruct](https://huggingface.co/LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct) | 7.8 | — | custom code |
| [c4ai-command-r7b-12-2024](https://huggingface.co/CohereLabs/c4ai-command-r7b-12-2024) | 8.0 | — | gated |
| [aya-expanse-8b](https://huggingface.co/CohereLabs/aya-expanse-8b) | 8.0 | — | multilingual, for the 11 non-English datasets; gated |
| [Llama-3.1-Tulu-3-8B](https://huggingface.co/allenai/Llama-3.1-Tulu-3-8B) | 8.0 | — | Llama-3.1-8B base with open post-training |
| [Mistral-Nemo-Instruct-2407](https://huggingface.co/mistralai/Mistral-Nemo-Instruct-2407) | 12.2 | — | |
| [gemma-2-9b-it](https://huggingface.co/google/gemma-2-9b-it) | 9.2 | — | gated |

## 4. Run, but not in the design

Kept for the record. Below about 1.5B a model either does not answer with a
digit or answers at random; that floor is a result in itself.

| model | params (B) | status | notes |
|---|--:|:-:|---|
| [MiniCPM5-2B](https://huggingface.co/openbmb/MiniCPM5-2B) | 2.5 | ✓ | usable, ρ median 0.29 |
| [SmolLM-1.7B-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM-1.7B-Instruct) | 1.7 | ✓ | no digit on any task |
| [SmolLM-360M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM-360M-Instruct) | 0.4 | ✓ | no digit on any task |
| [SmolLM2-135M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct) | 0.1 | ✓ | no digit on any task |

## Not planned

- Base (pre-trained) models and training checkpoints: they do not follow the
  instruction, so the reading has to be designed first. A separate experiment.
- Reasoning models without a thinking switch (DeepSeek-R1 distills).
- 70B-class models until the 32B results say it is worth two GPUs.
