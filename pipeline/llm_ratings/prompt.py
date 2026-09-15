"""Turn an instruction file + one stimulus into the exact string we score.

Instruction files carry a placeholder written as ``<<{word}>>`` /
``<<{sentence}>>`` / ``<<{items}>>`` / ``<<{expression}>>`` /
``<<{sentence_fragment}>>``. Every one of the 64 published instruction files
has exactly this form, so substitution is a plain regex.
"""

import re

PLACEHOLDER_RE = re.compile(r"<<\{([a-z_]+)\}>>")

#: how the stimulus replaces the placeholder
#:   quote - wrap in double quotes:           "the cat sat"      (default, and
#:           fixed across models: the <<...>> form is the instruction files'
#:           placeholder syntax leaking into the prompt, which participants
#:           never saw; agreed with Andrea 2026-09-07)
#:   angle - keep the file's own delimiters:  <<the cat sat>>
#:   raw   - bare text:                       the cat sat
PLACEHOLDER_STYLES = ("angle", "quote", "raw")


def read_instructions(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read().strip()


def placeholders(text):
    return PLACEHOLDER_RE.findall(text)


def fill(instruction_text, unit, style="quote"):
    if style not in PLACEHOLDER_STYLES:
        raise ValueError("style must be one of %s" % (PLACEHOLDER_STYLES,))
    unit = unit.strip()
    if style == "angle":
        repl = "<<%s>>" % unit
    elif style == "quote":
        repl = '"%s"' % unit
    else:
        repl = unit
    fields = set(PLACEHOLDER_RE.findall(instruction_text))
    if len(fields) > 1:
        # Every slot would receive the same string, so a template asking for a
        # sentence fragment *and* a target word would silently be handed the
        # target word twice and the model would never see the context. One
        # instruction file (devarda2023_predictability) is like this; refuse it
        # rather than score a prompt that does not pose the intended question.
        raise ValueError(
            "instruction needs %d different fields (%s) but a run supplies one "
            "unit; this task cannot be scored with a single-unit prompt"
            % (len(fields), ", ".join(sorted(fields))))
    out, n = PLACEHOLDER_RE.subn(lambda _m: repl, instruction_text)
    if n == 0:
        raise ValueError("instruction file has no <<{...}>> placeholder")
    return out


def build_prompt(instruction_text, unit, lo, hi, style="quote", suffix=None,
                 options=None):
    """Filled instructions plus an optional forced-format reminder.

    `options` is the surface forms actually being scored. It matters: with
    custom labels (--option-labels "No,Yes") a suffix that says "a single
    number from 0 to 1" contradicts the answers we score, and the model splits
    its mass between the two framings.
    """
    body = fill(instruction_text, unit, style=style)
    if suffix is None:
        suffix = ""
    elif suffix == "auto":
        default = [str(v) for v in range(lo, hi + 1)]
        if options is None or list(options) == default:
            suffix = ("\nRespond with a single number from %d to %d and nothing "
                      "else." % (lo, hi))
        else:
            suffix = ("\nRespond with exactly one of: %s. Nothing else."
                      % ", ".join(options))
    return body + suffix


def to_model_input(prompt, tokenizer, chat=True, system=None, answer_prefix=""):
    """Render the final string whose *next token* we read.

    chat=True  -> apply the tokenizer's chat template with a generation prompt
    chat=False -> plain completion; caller supplies e.g. answer_prefix="\\nAnswer:"
    """
    if not chat:
        return prompt + answer_prefix
    msgs = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    kwargs = {"tokenize": False, "add_generation_prompt": True}
    try:
        # Qwen3 and friends prepend a <think> block unless this is switched off.
        text = tokenizer.apply_chat_template(msgs, enable_thinking=False, **kwargs)
    except TypeError:
        text = tokenizer.apply_chat_template(msgs, **kwargs)
    return text + answer_prefix
