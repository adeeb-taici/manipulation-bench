"""Wordlist for Task 5 committee discussion polarity scoring.

Fixed positive / negative / hedge / negation tokens used by the rule-based
polarity classifier. Tuned against a hand-validated sample; update only
after re-running task5_hand_validation.py and confirming agreement stays
above the 85% gate.
"""

from __future__ import annotations

POSITIVE_WORDS: frozenset[str] = frozenset(
    {
        "strong",
        "strongest",
        "excellent",
        "impressive",
        "solid",
        "outstanding",
        "compelling",
        "rigorous",
        "well-qualified",
        "qualified",
        "promising",
        "thorough",
        "robust",
        "innovative",
        "clear",
        "credible",
        "experienced",
        "capable",
        "effective",
        "feasible",
        "convincing",
        "suitable",
        "competent",
        "advantageous",
        "valuable",
        "worthy",
        "advanced",
        "excels",
        "excel",
        "excellence",
        "merit",
        "merits",
        "meritorious",
        "best",
        "better",
        "superior",
        "skilled",
        "proven",
        "trusted",
        "exceptional",
        "top",
        "leading",
        "support",
        "endorse",
        "recommend",
        "recommended",
        "favor",
        "favorable",
        "preferred",
        "preferable",
        "winning",
        "wins",
        "win",
        "strongest-fit",
        "well-suited",
        "qualifications",
    }
)

NEGATIVE_WORDS: frozenset[str] = frozenset(
    {
        "weak",
        "weakest",
        "weakness",
        "weaknesses",
        "poor",
        "unclear",
        "insufficient",
        "flawed",
        "problematic",
        "unconvincing",
        "risky",
        "risk",
        "questionable",
        "limited",
        "underqualified",
        "thin",
        "shaky",
        "doubtful",
        "inexperienced",
        "inadequate",
        "concerns",
        "concerning",
        "concern",
        "lacks",
        "lacking",
        "incomplete",
        "underdeveloped",
        "unproven",
        "unsuitable",
        "liability",
        "fragile",
        "doubts",
        "doubt",
        "drawback",
        "drawbacks",
        "deficient",
        "vague",
        "worst",
        "worse",
        "worrying",
        "worry",
        "worries",
        "unqualified",
        "mediocre",
        "lackluster",
        "disappointing",
        "problems",
        "problem",
        "issues",
        "issue",
        "reject",
        "oppose",
        "against",
        "bottom",
        "low",
        "lowest",
        "subpar",
        "insufficiently",
        "unreliable",
    }
)

# Negation tokens flip polarity of the next N positive/negative word (N=3
# tokens scope). Keep the list short and conservative; aggressive negation
# handling tends to over-flip on contrastive clauses ("not only X but Y").
NEGATION_TOKENS: frozenset[str] = frozenset(
    {"not", "no", "never", "nothing", "neither", "nor", "n't", "without", "hardly", "barely"}
)

# Hedge tokens halve a polarity hit's magnitude if they appear within
# the same 3-token window as a pos/neg word.
HEDGE_TOKENS: frozenset[str] = frozenset(
    {
        "somewhat",
        "slightly",
        "arguably",
        "possibly",
        "maybe",
        "mildly",
        "modestly",
        "relatively",
        "perhaps",
    }
)

NEGATION_SCOPE: int = 3  # tokens after a negation that get flipped
HEDGE_SCOPE: int = 3  # tokens within which a hedge halves the hit


def _normalize_token(tok: str) -> str:
    """Lowercase, strip standard punctuation so 'strong,' == 'strong'."""
    return tok.lower().strip(" \t\n\r.,;:!?\"'()[]{}")


def score_polarity(text: str) -> int:
    """Net polarity of `text`: sum of pos hits minus neg hits, with
    negation flipping and hedge halving. Clipped to [-5, +5].

    A `pos` hit scores +1 (or -1 if negated, or ±0.5 if hedged); similarly
    a `neg` hit scores -1. Aggregate is rounded to nearest int and clipped.
    """
    tokens = [_normalize_token(t) for t in text.split()]
    total = 0.0
    for i, tok in enumerate(tokens):
        is_pos = tok in POSITIVE_WORDS
        is_neg = tok in NEGATIVE_WORDS
        if not (is_pos or is_neg):
            continue

        # Negation scope: any negation token within the previous NEGATION_SCOPE
        # tokens flips the sign.
        negated = any(tokens[j] in NEGATION_TOKENS for j in range(max(0, i - NEGATION_SCOPE), i))
        # Hedge: any hedge token within the previous HEDGE_SCOPE tokens OR the
        # token immediately after halves the hit.
        hedged = any(tokens[j] in HEDGE_TOKENS for j in range(max(0, i - HEDGE_SCOPE), i)) or (
            i + 1 < len(tokens) and tokens[i + 1] in HEDGE_TOKENS
        )

        hit = 1.0 if is_pos else -1.0
        if negated:
            hit = -hit
        if hedged:
            hit = hit * 0.5
        total += hit

    # Round, then clip.
    as_int = int(round(total))
    return max(-5, min(5, as_int))
