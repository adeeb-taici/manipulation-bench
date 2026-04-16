"""Tests for network structure metric scorers."""

from __future__ import annotations

import pytest

from manipulation_bench.scorers.network_metrics import (
    _compute_active_interface_density,
    _compute_echo_chamber_index,
    _compute_opinion_modularity,
    _compute_clustering_coefficient,
)


class TestComputeActiveInterfaceDensity:
    def test_all_same_opinion(self):
        edges = [("a", "b"), ("b", "c")]
        opinions = {"a": 0.5, "b": 0.5, "c": 0.5}
        result = _compute_active_interface_density(edges, opinions, threshold=0.1)
        assert result == pytest.approx(0.0)

    def test_all_different_opinions(self):
        edges = [("a", "b"), ("b", "c")]
        opinions = {"a": 0.0, "b": 0.5, "c": 1.0}
        result = _compute_active_interface_density(edges, opinions, threshold=0.1)
        assert result == pytest.approx(1.0)

    def test_mixed(self):
        edges = [("a", "b"), ("b", "c"), ("c", "d")]
        opinions = {"a": 0.5, "b": 0.5, "c": 0.9, "d": 0.9}
        result = _compute_active_interface_density(edges, opinions, threshold=0.1)
        # (a,b) same, (b,c) different, (c,d) same -> 1/3
        assert result == pytest.approx(1.0 / 3.0)

    def test_no_edges(self):
        opinions = {"a": 0.5}
        result = _compute_active_interface_density([], opinions, threshold=0.1)
        assert result == pytest.approx(0.0)

    def test_node_missing_from_opinions(self):
        edges = [("a", "b")]
        opinions = {"a": 0.5}  # b missing
        result = _compute_active_interface_density(edges, opinions, threshold=0.1)
        assert result == pytest.approx(0.0)


class TestComputeEchoChamberIndex:
    def test_perfect_echo_chamber(self):
        # Each node's opinion equals its neighbors' mean
        edges = [("a", "b"), ("c", "d")]
        opinions = {"a": 0.0, "b": 0.0, "c": 1.0, "d": 1.0}
        result = _compute_echo_chamber_index(edges, opinions)
        assert result == pytest.approx(1.0)

    def test_no_echo_chamber(self):
        # Alternating high/low connected to each other
        edges = [("a", "b"), ("c", "d")]
        opinions = {"a": 0.0, "b": 1.0, "c": 0.0, "d": 1.0}
        result = _compute_echo_chamber_index(edges, opinions)
        assert result == pytest.approx(-1.0)

    def test_no_edges(self):
        opinions = {"a": 0.5, "b": 0.7}
        result = _compute_echo_chamber_index([], opinions)
        assert result is None

    def test_single_edge_different_opinions(self):
        # Single edge: each node's neighbor mean is the other's opinion.
        # xs = [0.3, 0.7], ys = [0.7, 0.3] -> perfect anti-correlation (-1.0)
        edges = [("a", "b")]
        opinions = {"a": 0.3, "b": 0.7}
        result = _compute_echo_chamber_index(edges, opinions)
        assert result is not None

    def test_zero_variance_opinions(self):
        edges = [("a", "b"), ("b", "c")]
        opinions = {"a": 0.5, "b": 0.5, "c": 0.5}
        result = _compute_echo_chamber_index(edges, opinions)
        # Correlation undefined with zero variance
        assert result is None


class TestComputeOpinionModularity:
    def test_perfect_modularity(self):
        # Two groups, fully connected within, no edges between
        edges = [("a", "b"), ("c", "d")]
        opinions = {"a": 0.0, "b": 0.0, "c": 1.0, "d": 1.0}
        result = _compute_opinion_modularity(edges, opinions, threshold=0.3)
        assert result > 0.0

    def test_anti_modular(self):
        # All edges cross group boundaries
        edges = [("a", "c"), ("b", "d")]
        opinions = {"a": 0.0, "b": 0.0, "c": 1.0, "d": 1.0}
        result = _compute_opinion_modularity(edges, opinions, threshold=0.3)
        assert result < 0.0

    def test_no_edges(self):
        opinions = {"a": 0.5}
        result = _compute_opinion_modularity([], opinions, threshold=0.3)
        assert result == pytest.approx(0.0)

    def test_single_community(self):
        edges = [("a", "b"), ("b", "c")]
        opinions = {"a": 0.5, "b": 0.5, "c": 0.5}
        result = _compute_opinion_modularity(edges, opinions, threshold=0.3)
        # All same community, modularity ~0
        assert abs(result) < 0.5


class TestComputeClusteringCoefficient:
    def test_complete_graph(self):
        # Triangle: clustering = 1.0
        edges = [("a", "b"), ("b", "c"), ("a", "c")]
        result = _compute_clustering_coefficient(edges)
        assert result == pytest.approx(1.0)

    def test_no_triangles(self):
        # Line: a-b-c, no triangle
        edges = [("a", "b"), ("b", "c")]
        result = _compute_clustering_coefficient(edges)
        assert result == pytest.approx(0.0)

    def test_no_edges(self):
        result = _compute_clustering_coefficient([])
        assert result == pytest.approx(0.0)

    def test_single_edge(self):
        edges = [("a", "b")]
        result = _compute_clustering_coefficient(edges)
        assert result == pytest.approx(0.0)

    def test_partial_clustering(self):
        # Square with one diagonal: a-b, b-c, c-d, d-a, a-c
        edges = [("a", "b"), ("b", "c"), ("c", "d"), ("d", "a"), ("a", "c")]
        result = _compute_clustering_coefficient(edges)
        assert 0.0 < result < 1.0


# ---------------------------------------------------------------------------
# Scorer wrapper tests
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock

from inspect_ai.util import Store

from manipulation_bench.models import AgentSnapshot, InteractionState, NetworkSnapshot
from manipulation_bench.scorers.network_metrics import (
    active_interface_density,
    echo_chamber_index,
    opinion_modularity,
    clustering_coefficient,
)


def _make_state_with_network(
    opinions_per_agent: dict[str, list[float | None]],
    edges: list[tuple[str, str]],
) -> MagicMock:
    """Build a mock TaskState with InteractionState containing agents + network snapshot.

    Each call creates a fresh Store to avoid cross-test contamination from the
    StoreModel's class-level default store.
    """
    fresh_store = Store()
    interaction = InteractionState(
        store=fresh_store,
        agent_states={
            name: AgentSnapshot(opinions=ops)
            for name, ops in opinions_per_agent.items()
        },
        agent_names=list(opinions_per_agent.keys()),
        network_snapshots=[
            NetworkSnapshot(round=0, edges=edges),
        ],
    )
    state = MagicMock()
    state.store_as.return_value = interaction
    return state


def _make_state_no_snapshots(
    opinions_per_agent: dict[str, list[float | None]],
) -> MagicMock:
    """Build a mock TaskState with InteractionState but no network snapshots."""
    fresh_store = Store()
    interaction = InteractionState(
        store=fresh_store,
        agent_states={
            name: AgentSnapshot(opinions=ops)
            for name, ops in opinions_per_agent.items()
        },
        agent_names=list(opinions_per_agent.keys()),
        network_snapshots=[],
    )
    state = MagicMock()
    state.store_as.return_value = interaction
    return state


class TestActiveInterfaceDensityScorer:
    @pytest.mark.asyncio
    async def test_basic(self):
        state = _make_state_with_network(
            opinions_per_agent={"a": [0.0], "b": [1.0]},
            edges=[("a", "b")],
        )
        scorer_fn = active_interface_density()
        result = await scorer_fn(state, MagicMock())
        assert result.value == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_no_snapshots_returns_none(self):
        state = _make_state_no_snapshots({"a": [0.5]})
        scorer_fn = active_interface_density()
        result = await scorer_fn(state, MagicMock())
        assert result.value.get("result") is None  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_no_opinions_returns_none(self):
        fresh_store = Store()
        interaction = InteractionState(
            store=fresh_store,
            agent_states={"a": AgentSnapshot(opinions=[])},
            agent_names=["a"],
            network_snapshots=[NetworkSnapshot(round=0, edges=[("a", "b")])],
        )
        state = MagicMock()
        state.store_as.return_value = interaction
        scorer_fn = active_interface_density()
        result = await scorer_fn(state, MagicMock())
        assert result.value.get("result") is None  # type: ignore[union-attr]


class TestEchoChamberIndexScorer:
    @pytest.mark.asyncio
    async def test_no_snapshots_returns_none(self):
        state = _make_state_no_snapshots({"a": [0.5]})
        scorer_fn = echo_chamber_index()
        result = await scorer_fn(state, MagicMock())
        assert result.value.get("result") is None  # type: ignore[union-attr]


class TestOpinionModularityScorer:
    @pytest.mark.asyncio
    async def test_basic(self):
        state = _make_state_with_network(
            opinions_per_agent={"a": [0.0], "b": [0.0], "c": [1.0], "d": [1.0]},
            edges=[("a", "b"), ("c", "d")],
        )
        scorer_fn = opinion_modularity()
        result = await scorer_fn(state, MagicMock())
        assert result.value is not None
        assert result.value > 0.0


class TestClusteringCoefficientScorer:
    @pytest.mark.asyncio
    async def test_triangle(self):
        state = _make_state_with_network(
            opinions_per_agent={"a": [0.5], "b": [0.5], "c": [0.5]},
            edges=[("a", "b"), ("b", "c"), ("a", "c")],
        )
        scorer_fn = clustering_coefficient()
        result = await scorer_fn(state, MagicMock())
        assert result.value == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_no_snapshots_returns_none(self):
        state = _make_state_no_snapshots({"a": [0.5]})
        scorer_fn = clustering_coefficient()
        result = await scorer_fn(state, MagicMock())
        assert result.value.get("result") is None  # type: ignore[union-attr]
