"""manipulation-bench — multi-agent evaluation framework for studying manipulation in AI interactions.

Built on Inspect AI. Lets you measure how AI models manipulate and respond to
manipulation across debates, social-deduction games (Werewolf), negotiation
(Diplomacy / Bargaining), public-goods (Village Commons), single-agent
representation (Sales), committee evaluation with conflict of interest, and
inbox triage. Every environment shares the same response-surface
parameterization (frame x incentive x difficulty), so results can be compared
cross-environment with a unified analyzer.

Common entry points:

- :mod:`manipulation_bench.cli` — the ``mb`` console script (``mb run``,
  ``mb envs``, ``mb analyze``).
- :mod:`manipulation_bench.axes` — canonical response-surface axes and
  per-environment frame / incentive prompt fragments.
- :mod:`manipulation_bench.environments` — environment ABC plus the
  Debate / Werewolf / Diplomacy / Village / Committee implementations.
- :mod:`manipulation_bench.scorers` — LLM-judge, statistical, and
  mathematical scorers per environment.
- :mod:`manipulation_bench.task`, :mod:`.game_task`, :mod:`.diplomacy_task`,
  :mod:`.village_task`, :mod:`.sales_task`, :mod:`.committee_task`,
  :mod:`.bargaining_task`, :mod:`.inbox_task` — Inspect AI ``@task`` entry
  points.

See the top-level ``README.md`` for the quickstart and ``examples/`` for
templates on adding a new environment or scorer.
"""
