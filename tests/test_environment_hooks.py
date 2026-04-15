"""Tests for new optional Environment hooks."""

from manipulation_bench.environments.base import Environment, Phase, PhaseType


class TestPhaseParallel:
    def test_default_not_parallel(self):
        phase = Phase(name="test", phase_type=PhaseType.DISCUSSION, round=0, acting_agents=["a"])
        assert phase.parallel is False

    def test_parallel_flag(self):
        phase = Phase(
            name="test", phase_type=PhaseType.DISCUSSION, round=0,
            acting_agents=["a", "b"], parallel=True,
        )
        assert phase.parallel is True


class TestDefaultHooks:
    """Test that default hook implementations return expected values."""

    def test_extract_opinion_default(self):
        from manipulation_bench.environments.debate import DebateEnvironment
        env = DebateEnvironment()
        env.setup(["alice", "bob"])
        assert env.extract_opinion("alice", "I think X") is None

    def test_classify_stance_default(self):
        from manipulation_bench.environments.debate import DebateEnvironment
        env = DebateEnvironment()
        env.setup(["alice", "bob"])
        assert env.classify_stance("alice", "I agree") == "unknown"

    def test_get_feed_filter_default(self):
        from manipulation_bench.environments.debate import DebateEnvironment
        env = DebateEnvironment()
        env.setup(["alice", "bob"])
        assert env.get_feed_filter("alice") is None
