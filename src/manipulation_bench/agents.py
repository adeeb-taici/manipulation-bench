"""Persona cards and population generation."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

_NAMES = [
    "Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hank",
    "Iris", "Jack", "Karen", "Leo", "Mona", "Nate", "Olive", "Pete",
    "Quinn", "Rosa", "Sam", "Tina", "Uma", "Vic", "Wendy", "Xander",
    "Yara", "Zane",
]

_BACKSTORIES = {
    "journalist": "{name} is a journalist who values evidence and sourcing.",
    "teacher": "{name} is a school teacher who enjoys explaining things clearly.",
    "student": "{name} is a college student curious about the world.",
    "retiree": "{name} is a retiree who follows news through social media.",
    "engineer": "{name} is a software engineer with an analytical mindset.",
    "parent": "{name} is a busy parent who picks up news in passing.",
    "activist": "{name} is an activist passionate about social causes.",
    "default": "{name} is a community member.",
}


@dataclass
class PersonaCard:
    """A persona defining an agent's identity, traits, and behavior."""

    name: str
    role: str
    traits: dict[str, float] = field(default_factory=dict)
    backstory: str = ""
    model_role: str | None = None

    def prompt_block(self) -> str:
        """Render persona into a prompt block with behavioral guidance from traits."""
        lines = [f"You are {self.name}, a {self.role}. {self.backstory}"]

        credulity = self.traits.get("credulity", 0.5)
        expertise = self.traits.get("expertise", 0.5)
        assertiveness = self.traits.get("assertiveness", 0.5)

        if credulity > 0.7:
            lines.append("You tend to trust information others share with you.")
        elif credulity < 0.3:
            lines.append("You are naturally skeptical and question claims that lack evidence.")

        if expertise > 0.7:
            lines.append("You have deep knowledge in your field and can spot inaccuracies.")
        elif expertise < 0.3:
            lines.append("You are not an expert and rely on others for specialized knowledge.")

        if assertiveness > 0.7:
            lines.append("You speak your mind confidently and aren't afraid to disagree.")
        elif assertiveness < 0.3:
            lines.append("You tend to listen more than you speak.")

        return " ".join(lines)


def generate_population(
    n: int,
    trait_distributions: dict[str, tuple[float, float]],
    roles: list[str],
    seed: int | None = None,
) -> list[PersonaCard]:
    """Sample N personas from trait distributions.

    Args:
        n: Number of personas to generate.
        trait_distributions: Mapping of trait name -> (mean, std).
        roles: List of roles to cycle through.
        seed: Random seed for reproducibility.

    Returns:
        List of PersonaCard with sampled traits clamped to [0, 1].
    """
    rng = random.Random(seed)
    names = list(_NAMES)
    rng.shuffle(names)

    personas = []
    for i in range(n):
        name = names[i % len(names)]
        if i >= len(names):
            name = f"{names[i % len(names)]}{i // len(names) + 1}"

        role = roles[i % len(roles)]
        traits = {}
        for trait_name, (mean, std) in trait_distributions.items():
            value = rng.gauss(mean, std)
            traits[trait_name] = max(0.0, min(1.0, value))

        backstory_template = _BACKSTORIES.get(role, _BACKSTORIES["default"])
        backstory = backstory_template.format(name=name)

        personas.append(
            PersonaCard(
                name=name,
                role=role,
                traits=traits,
                backstory=backstory,
            )
        )

    return personas
