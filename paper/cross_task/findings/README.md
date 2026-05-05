# Findings index

Cross-cutting findings from the manipulation-bench project. Per-task findings
live with their tasks (`paper/task<N>/results.md`).

## Synthesis (start here)

- [`consolidated.md`](consolidated.md) — master synthesis with conflict resolution across all 4 sources
- [`notes.md`](notes.md) — mid-level synthesis: 5 robust claims + 5 conflicts resolved
- [`exploratory.md`](exploratory.md) — post-PREREG analyses on combined eval logs
- [`first_principles.md`](first_principles.md) — independent bottom-up reanalysis of `data/results.csv`

## Corpus analysis (the 26k-row trajectory CSV)

- [`corpus.md`](corpus.md) — full corpus analysis with cluster-bootstrap CIs
  - Scripts: [`../scripts/corpus/`](../scripts/corpus/)
  - Figures: [`../figures/corpus/`](../figures/corpus/)
  - Data: [`../data/corpus.csv`](../data/corpus.csv)

## Newer statistical analyses (mixed-effects, multi-test, bootstrap)

- [`newer_analysis.md`](newer_analysis.md) — three statistical gap-fillers + incentive forest plot
- [`incentive_recode_impact.md`](incentive_recode_impact.md) — paper.tex edits required after Bargaining incentive label inversion
- [`spearman_bootstrap.md`](spearman_bootstrap.md) — bootstrap CIs on the rank-instability headline
- [`methods.md`](methods.md) — terse list of every statistical procedure
- [`refusal_scan.md`](refusal_scan.md) — refusal/non-compliance scan across canonical roster
- [`incentive_traces.md`](incentive_traces.md) — reasoning traces for high-incentive deterrence
  - Scripts: [`../scripts/newer/`](../scripts/newer/)
  - Figures: [`../figures/newer/`](../figures/newer/)

## Capability axis (LMArena ELO, tier, generation)

- [`capability_eval.md`](capability_eval.md) — post-hoc capability axis analysis
- [`capability_eval_README.md`](capability_eval_README.md) — overview + scope
  - Scripts: [`../scripts/capability/`](../scripts/capability/)
  - Figures: [`../figures/capability/`](../figures/capability/)

## v2 paper reanalysis

- [`reanalysis_notes.md`](reanalysis_notes.md) — v2 statistical reanalysis notes
  - Scripts: [`../scripts/cross_task/`](../scripts/cross_task/)
  - Analysis JSONs: [`../analysis/`](../analysis/)

## Legacy pre-paper

- [`legacy_pre_paper.md`](legacy_pre_paper.md) — frozen pre-paper exploratory log (4-model roster, last runs 2026-04-15/16)
