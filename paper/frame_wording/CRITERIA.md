# Frame-wording check — pre-specified criteria

**Locked 2026-07-31, before any frame-wording model call.** Answers kcqH W4: with one prompt
wording per cell, could a paraphrase shift a slope enough to flip a dominance ranking in a
borderline environment? T5 Committee and T6 Inbox are tested because they have the two smallest
dominance margins; T6 is additionally where the reduced protocol is least trustworthy
(1.44× margin, expansion-flagged in `REDUCED_PROTOCOL_RETROSPECTIVE.md`).

## Criteria

1. **Dominance stability — the registered question.** For each environment and each variant, the
   dominant axis recomputed with the variant frame slope matches the original. Reported per
   variant per environment. The frame slope is recomputed on the swept cell; the incentive and
   difficulty slopes are the published full-design values, which are unchanged by construction
   because no incentive or difficulty text is touched.

2. **Slope stability — context for (1).** Variant frame slopes fall within the band the existing
   paraphrase analysis established (Appendix F held within ~20%). The actual spread is reported
   whether or not it falls in that band.

3. **A flip is reported as a flip**, with the margin. Both environments were chosen because they
   are borderline. A flip is a possible honest outcome: it would narrow the paper's dominance
   claim for that environment. It would not break the taxonomy, and it will not be smoothed over.

## Design as locked

| | |
|---|---|
| Varies | frame-axis prompt wording only |
| Held byte-identical | incentive text, difficulty substrate/slate, scoring, agent layout, models |
| Versions | v1 = frozen production wording (diff-checked byte-identical), v2 = formal-imperative, v3 = conversational |
| Committee cell | incentive=none, difficulty=medium |
| Inbox cell | incentive=high, difficulty=medium |
| Roster | claude, gpt55, gemini, **grok43**, llama, deepseek — Grok 4 deprecated, Grok 4.3 substituted with its own v1 arm so its contrast is internally valid |
| Scenarios | Committee 270 (6 × 5 frames × 3 versions × 3 medium slates); Inbox 360 (6 × 5 × 3 × 2 substrates × 2 reps) |

Cells were picked by the Appendix F rule: the (incentive, difficulty) cell whose |frame slope| is
closest to the per-task mean. Only that slice runs, because the registered question is about the
frame slope and the dominance ordering it produces, not about re-measuring the full surface.

## Two levels flagged before running

- **T6 `minimal` is the empty string** in the frozen design and cannot be paraphrased. Its three
  arms are byte-identical, which makes it an **internal negative control**: its spread is
  run-to-run noise only, and provides the null band against which the other levels' spread is
  read.
- **T5 `minimal` is near-trivial to paraphrase** — three short declaratives, no directive verb, no
  consequence clause — so v2/v3 vary diction only. Low variation there is a property of the level.

## T5 specifics

- Only the `interested` text varies. `initial_rating_bias` scores the interested party's own
  **pre-discussion private** rating (`committee.py:349`, never surfaced to other agents), so
  neutral-panel wording cannot affect it by construction. Neutral text is held byte-identical,
  verified in the generated scenarios.
- The **per-sample scale correction** (max rating ≤ 10 ⇒ ×2) is applied before any cross-model
  quantity.
- **Scale adherence is recorded per version.** A wording change could plausibly shift
  prose-vs-schema adherence. If it does, that is a finding, not noise.

## Attrition

Per-arm attrition is reported as the salience experiment did. Failed samples are not silently
retried into a mixed log; any re-run is recorded with its arm and count.
