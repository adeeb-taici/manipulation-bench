"""Generic mitigation / defense interface.

A :class:`Mitigation` is a plug-in that the unified solver applies at three
points in every turn of a ``game_solver.py`` environment (debate, werewolf,
diplomacy, village, committee). Defenses subclass this and override only the
hook(s) they need — the others are no-ops, so a typical defense is a few lines.

The three hooks, in the order the solver runs them:

  1. ``transform_agent``   — once per agent, before the loop. Rewrite the
     :class:`AgentRole` (e.g. append a skeptical-framing suffix to a
     *protected* agent's system prompt). Pure / synchronous.
  2. ``transform_messages``— per turn, after the solver builds the agent's
     message view but before ``model.generate``. Async (a defense may call
     out to another model). Return the (possibly rewritten) message list.
  3. ``transform_response``— per turn, after ``model.generate``. Async.
     Inspect / flag / redact / rewrite the model output before it is
     delivered to other agents. This is where a critic-monitor defense lives.

Targeting (who is the manipulator vs. who to protect) is read from
``AgentRole.adversary`` via :func:`manipulation_bench.mitigations._targeting.is_adversary`.

Resolution (CLI ``-T mitigations=prompt_suffix,critic_monitor``) mirrors the
scorer resolver — see :mod:`manipulation_bench.mitigations._resolve`.
"""

from __future__ import annotations

from abc import ABC

from inspect_ai.model import ChatMessage, ModelOutput

from manipulation_bench.models import AgentRole, ScenarioConfig


class Mitigation(ABC):
    """Base class for manipulation defenses. Override only the hooks you need."""

    #: short identifier stamped into ``Turn.metadata['mitigations_applied']``
    #: and used in logging. Subclasses should set this.
    name: str = "mitigation"

    def transform_agent(self, agent: AgentRole, scenario: ScenarioConfig) -> AgentRole:
        """Rewrite an agent's role before the interaction loop. Default: no-op.

        ``AgentRole`` is frozen — return ``agent.model_copy(update={...})`` to
        change it rather than mutating in place.
        """
        return agent

    async def transform_messages(
        self,
        agent: AgentRole,
        messages: list[ChatMessage],
        scenario: ScenarioConfig,
    ) -> list[ChatMessage]:
        """Rewrite the message view passed to ``model.generate``. Default: no-op."""
        return messages

    async def transform_response(
        self,
        agent: AgentRole,
        messages: list[ChatMessage],
        output: ModelOutput,
        scenario: ScenarioConfig,
    ) -> ModelOutput:
        """Rewrite the model output before it is delivered. Default: no-op.

        A ``transform_response`` that drops ``output.message.tool_calls`` in an
        ACTION phase will make the solver treat the turn as a missing tool call
        and consume one retry (see ``game_solver.py``). That is intended — call
        it out if your defense does this on purpose.
        """
        return output
