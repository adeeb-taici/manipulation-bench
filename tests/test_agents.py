"""Tests for PersonaCard and population generation."""

from manipulation_bench.agents import PersonaCard, generate_population


class TestPersonaCard:
    def test_create_minimal(self):
        p = PersonaCard(name="Alice", role="journalist")
        assert p.name == "Alice"
        assert p.role == "journalist"
        assert p.traits == {}
        assert p.backstory == ""
        assert p.model_role is None

    def test_create_with_traits(self):
        p = PersonaCard(
            name="Bob",
            role="engineer",
            traits={"credulity": 0.8, "expertise": 0.6, "assertiveness": 0.3},
            backstory="Bob is a software engineer.",
            model_role="agent_a",
        )
        assert p.traits["credulity"] == 0.8
        assert p.model_role == "agent_a"

    def test_prompt_block_high_credulity(self):
        p = PersonaCard(
            name="Alice",
            role="journalist",
            traits={"credulity": 0.9, "expertise": 0.5, "assertiveness": 0.5},
            backstory="Alice is a journalist.",
        )
        block = p.prompt_block()
        assert "Alice" in block
        assert "journalist" in block
        assert "trust" in block.lower()

    def test_prompt_block_low_credulity(self):
        p = PersonaCard(
            name="Bob",
            role="engineer",
            traits={"credulity": 0.1, "expertise": 0.5, "assertiveness": 0.5},
            backstory="Bob is an engineer.",
        )
        block = p.prompt_block()
        assert "skeptical" in block.lower()

    def test_prompt_block_no_traits(self):
        p = PersonaCard(name="Carol", role="student")
        block = p.prompt_block()
        assert "Carol" in block
        assert "student" in block


class TestGeneratePopulation:
    def test_correct_count(self):
        personas = generate_population(
            n=5,
            trait_distributions={"credulity": (0.5, 0.15)},
            roles=["journalist", "teacher"],
            seed=42,
        )
        assert len(personas) == 5

    def test_deterministic_with_seed(self):
        kwargs = dict(
            n=3,
            trait_distributions={"credulity": (0.5, 0.15), "expertise": (0.5, 0.2)},
            roles=["journalist"],
            seed=42,
        )
        a = generate_population(**kwargs)
        b = generate_population(**kwargs)
        assert [p.name for p in a] == [p.name for p in b]
        assert [p.traits for p in a] == [p.traits for p in b]

    def test_traits_clamped(self):
        personas = generate_population(
            n=50,
            trait_distributions={"credulity": (0.5, 10.0)},
            roles=["student"],
            seed=42,
        )
        for p in personas:
            assert 0.0 <= p.traits["credulity"] <= 1.0

    def test_roles_cycle(self):
        personas = generate_population(
            n=5,
            trait_distributions={"credulity": (0.5, 0.1)},
            roles=["journalist", "teacher"],
            seed=42,
        )
        assert personas[0].role == "journalist"
        assert personas[1].role == "teacher"
        assert personas[2].role == "journalist"

    def test_backstory_generated(self):
        personas = generate_population(
            n=1,
            trait_distributions={},
            roles=["journalist"],
            seed=42,
        )
        assert "journalist" in personas[0].backstory.lower()

    def test_names_unique_when_small(self):
        personas = generate_population(
            n=5,
            trait_distributions={},
            roles=["student"],
            seed=42,
        )
        names = [p.name for p in personas]
        assert len(names) == len(set(names))
