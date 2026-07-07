Dentella et al. (2023) grammaticality data

Final scale:
- 1 = the sentence is grammatical / the statement "this sentence is grammatical" is true
- 0 = the sentence is ungrammatical / the statement "this sentence is grammatical" is false

Rationale for 0/1 conversion:
The original repository encodes participant performance with an accuracy variable, where
0 = incorrect and 1 = correct. It also encodes the true grammatical status of each sentence
with a condition variable, where 0 = grammatical and 1 = ungrammatical. To make the data
match the LLM instruction format, I converted each participant trial into a direct grammaticality
judgment:

- grammatical sentence + correct response -> 1
- grammatical sentence + incorrect response -> 0
- ungrammatical sentence + correct response -> 0
- ungrammatical sentence + incorrect response -> 1

This yields the participant's implied answer to the question: "Is this sentence grammatical?"
The converted responses are therefore direct binary judgments, not accuracy scores.

Important interpretation note:
Because the released human data encode correctness relative to the sentence's true condition,
the 0/1 grammaticality judgment had to be derived from both condition and accuracy. Reading
accuracy alone as the rating would be incorrect: for ungrammatical sentences, a correct response
means the participant judged the sentence as ungrammatical, which maps to 0 on this final
true/false grammaticality scale.
