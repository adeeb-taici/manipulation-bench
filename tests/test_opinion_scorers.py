"""Tests for opinion distribution scorers."""

from __future__ import annotations

import math

import pytest

from manipulation_bench.scorers.opinion import (
    _compute_mean_opinion,
    _compute_opinion_spread,
    _compute_mean_absolute_difference,
    _compute_esteban_ray_index,
    _compute_inverse_simpson,
    _compute_shannon_entropy,
    _compute_bimodality_coefficient,
)


class TestComputeMeanOpinion:
    def test_basic(self):
        assert _compute_mean_opinion([0.0, 1.0]) == pytest.approx(0.5)

    def test_single_value(self):
        assert _compute_mean_opinion([0.7]) == pytest.approx(0.7)

    def test_uniform(self):
        assert _compute_mean_opinion([0.5, 0.5, 0.5]) == pytest.approx(0.5)

    def test_asymmetric(self):
        assert _compute_mean_opinion([0.0, 0.0, 1.0]) == pytest.approx(1.0 / 3.0)


class TestComputeOpinionSpread:
    def test_no_spread(self):
        assert _compute_opinion_spread([0.5, 0.5, 0.5]) == pytest.approx(0.0)

    def test_maximum_spread(self):
        # Two values at extremes: std = 0.5, normalized by opinion range (assume 0-1)
        result = _compute_opinion_spread([0.0, 1.0])
        assert result > 0.0

    def test_single_value(self):
        assert _compute_opinion_spread([0.7]) == pytest.approx(0.0)

    def test_moderate_spread(self):
        result = _compute_opinion_spread([0.3, 0.5, 0.7])
        assert 0.0 < result < 1.0


class TestComputeMeanAbsoluteDifference:
    def test_identical(self):
        assert _compute_mean_absolute_difference([0.5, 0.5, 0.5]) == pytest.approx(0.0)

    def test_two_values(self):
        # |0.0 - 1.0| = 1.0, only one pair
        assert _compute_mean_absolute_difference([0.0, 1.0]) == pytest.approx(1.0)

    def test_three_values(self):
        # pairs: |0-0.5|=0.5, |0-1|=1.0, |0.5-1|=0.5 -> mean = 2.0/3
        result = _compute_mean_absolute_difference([0.0, 0.5, 1.0])
        assert result == pytest.approx(2.0 / 3.0)

    def test_single_value(self):
        assert _compute_mean_absolute_difference([0.5]) == pytest.approx(0.0)


class TestComputeEstebanRayIndex:
    def test_consensus(self):
        # All at same value -> no polarization
        assert _compute_esteban_ray_index([0.5, 0.5, 0.5, 0.5]) == pytest.approx(0.0)

    def test_bimodal_polarization(self):
        # Two clusters far apart -> high polarization
        opinions = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]
        result = _compute_esteban_ray_index(opinions)
        assert result > 0.0

    def test_single_value(self):
        assert _compute_esteban_ray_index([0.5]) == pytest.approx(0.0)

    def test_moderate_polarization(self):
        # Some spread but not bimodal
        opinions = [0.2, 0.3, 0.7, 0.8]
        result = _compute_esteban_ray_index(opinions)
        assert result > 0.0

    def test_more_polarized_scores_higher(self):
        mild = [0.4, 0.45, 0.55, 0.6]
        extreme = [0.0, 0.0, 1.0, 1.0]
        assert _compute_esteban_ray_index(extreme) > _compute_esteban_ray_index(mild)


class TestComputeInverseSimpson:
    def test_all_same_bin(self):
        # All opinions in same bin -> 1 effective cluster
        result = _compute_inverse_simpson([0.5, 0.5, 0.5])
        assert result == pytest.approx(1.0)

    def test_two_equal_bins(self):
        # Half in [0, 0.1), half in [0.9, 1.0) -> 2 effective clusters
        result = _compute_inverse_simpson([0.0, 0.0, 0.0, 1.0, 1.0, 1.0])
        assert result == pytest.approx(2.0)

    def test_single_value(self):
        result = _compute_inverse_simpson([0.5])
        assert result == pytest.approx(1.0)

    def test_uniform_distribution(self):
        # Spread across many bins -> high effective count
        opinions = [i / 9.0 for i in range(10)]
        result = _compute_inverse_simpson(opinions)
        assert result > 1.0


class TestComputeShannonEntropy:
    def test_all_same_bin(self):
        result = _compute_shannon_entropy([0.5, 0.5, 0.5])
        assert result == pytest.approx(0.0)

    def test_two_equal_bins(self):
        result = _compute_shannon_entropy([0.0, 0.0, 0.0, 1.0, 1.0, 1.0])
        assert result == pytest.approx(math.log2(2))

    def test_single_value(self):
        result = _compute_shannon_entropy([0.5])
        assert result == pytest.approx(0.0)

    def test_more_spread_higher_entropy(self):
        clustered = [0.5, 0.5, 0.5, 0.5]
        spread = [0.1, 0.3, 0.6, 0.9]
        assert _compute_shannon_entropy(spread) > _compute_shannon_entropy(clustered)


class TestComputeBimodalityCoefficient:
    def test_uniform_not_bimodal(self):
        # Tight cluster around 0.5 -> near-zero skewness and kurtosis close to 3,
        # giving bimodality coefficient well below 0.555
        opinions = [0.45, 0.47, 0.49, 0.50, 0.51, 0.53, 0.55] * 5
        result = _compute_bimodality_coefficient(opinions)
        assert result < 0.555

    def test_bimodal(self):
        # Strong bimodal -> high coefficient
        opinions = [0.0] * 20 + [1.0] * 20
        result = _compute_bimodality_coefficient(opinions)
        assert result > 0.555

    def test_too_few_values(self):
        # Need at least 3 values for meaningful kurtosis
        assert _compute_bimodality_coefficient([0.5, 0.5]) is None

    def test_single_value(self):
        assert _compute_bimodality_coefficient([0.5]) is None

    def test_zero_variance(self):
        # All identical -> kurtosis undefined, return None
        assert _compute_bimodality_coefficient([0.5, 0.5, 0.5, 0.5]) is None


# ---------------------------------------------------------------------------
# Scorer wrapper tests
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock

from inspect_ai.util import Store

from manipulation_bench.models import AgentSnapshot, InteractionState
from manipulation_bench.scorers.opinion import (
    mean_opinion,
    opinion_spread,
    mean_absolute_difference,
    esteban_ray_index,
    inverse_simpson,
    shannon_entropy,
    bimodality_coefficient,
)


def _make_state_with_opinions(opinions_per_agent: dict[str, list[float | None]]) -> MagicMock:
    """Build a mock TaskState with InteractionState containing agent opinions.

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
    )
    state = MagicMock()
    state.store_as.return_value = interaction
    return state


class TestMeanOpinionScorer:
    @pytest.mark.asyncio
    async def test_basic(self):
        state = _make_state_with_opinions({
            "alice": [0.0, 0.2],
            "bob": [1.0, 0.8],
        })
        scorer_fn = mean_opinion()
        result = await scorer_fn(state, MagicMock())
        assert result.value == pytest.approx(0.5)  # mean of [0.2, 0.8]

    @pytest.mark.asyncio
    async def test_no_opinions_returns_none(self):
        state = _make_state_with_opinions({
            "alice": [],
            "bob": [],
        })
        scorer_fn = mean_opinion()
        result = await scorer_fn(state, MagicMock())
        assert result.value.get("result") is None  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_all_none_opinions_returns_none(self):
        state = _make_state_with_opinions({
            "alice": [None, None],
            "bob": [None, None],
        })
        scorer_fn = mean_opinion()
        result = await scorer_fn(state, MagicMock())
        assert result.value.get("result") is None  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_mixed_none_and_real(self):
        state = _make_state_with_opinions({
            "alice": [None, 0.4],
            "bob": [None, None],  # no final opinion
            "carol": [0.1, 0.6],
        })
        scorer_fn = mean_opinion()
        result = await scorer_fn(state, MagicMock())
        # final opinions: alice=0.4, carol=0.6, bob excluded
        assert result.value == pytest.approx(0.5)


class TestOpinionSpreadScorer:
    @pytest.mark.asyncio
    async def test_no_opinions_returns_none(self):
        state = _make_state_with_opinions({"alice": []})
        scorer_fn = opinion_spread()
        result = await scorer_fn(state, MagicMock())
        assert result.value.get("result") is None  # type: ignore[union-attr]


class TestMeanAbsoluteDifferenceScorer:
    @pytest.mark.asyncio
    async def test_identical_opinions(self):
        state = _make_state_with_opinions({
            "alice": [0.5],
            "bob": [0.5],
            "carol": [0.5],
        })
        scorer_fn = mean_absolute_difference()
        result = await scorer_fn(state, MagicMock())
        assert result.value == pytest.approx(0.0)


class TestEstebanRayIndexScorer:
    @pytest.mark.asyncio
    async def test_no_opinions_returns_none(self):
        state = _make_state_with_opinions({"alice": [], "bob": []})
        scorer_fn = esteban_ray_index()
        result = await scorer_fn(state, MagicMock())
        assert result.value.get("result") is None  # type: ignore[union-attr]


class TestInverseSimpsonScorer:
    @pytest.mark.asyncio
    async def test_all_same(self):
        state = _make_state_with_opinions({
            "a": [0.5], "b": [0.5], "c": [0.5],
        })
        scorer_fn = inverse_simpson()
        result = await scorer_fn(state, MagicMock())
        assert result.value == pytest.approx(1.0)


class TestShannonEntropyScorer:
    @pytest.mark.asyncio
    async def test_all_same(self):
        state = _make_state_with_opinions({
            "a": [0.5], "b": [0.5], "c": [0.5],
        })
        scorer_fn = shannon_entropy()
        result = await scorer_fn(state, MagicMock())
        assert result.value == pytest.approx(0.0)


class TestBimodalityCoefficientScorer:
    @pytest.mark.asyncio
    async def test_too_few_returns_none(self):
        state = _make_state_with_opinions({
            "a": [0.5], "b": [0.5],
        })
        scorer_fn = bimodality_coefficient()
        result = await scorer_fn(state, MagicMock())
        assert result.value.get("result") is None  # type: ignore[union-attr]
