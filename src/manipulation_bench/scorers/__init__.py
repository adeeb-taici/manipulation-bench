from manipulation_bench.scorers.behavioral import (
    argument_novelty,
    backfire_rate,
    persona_consistency,
    rhetoric_classification,
    sycophancy_rate,
)
from manipulation_bench.scorers.dynamics import (
    deception_detection_rate,
    faction_survival_time,
    influence_asymmetry,
    opinion_change_rate,
    time_to_consensus,
)
from manipulation_bench.scorers.grounded import ground_truth_persuasion
from manipulation_bench.scorers.judges import (
    argument_quality,
    belief_shift,
    manipulation_detection,
)
from manipulation_bench.scorers.negotiation import (
    agreement_compliance,
    negotiation_manipulation,
    territorial_success,
)
from manipulation_bench.scorers.network_metrics import (
    active_interface_density,
    clustering_coefficient,
    echo_chamber_index,
    opinion_modularity,
)
from manipulation_bench.scorers.opinion import (
    bimodality_coefficient,
    esteban_ray_index,
    inverse_simpson,
    mean_absolute_difference,
    mean_opinion,
    opinion_spread,
    shannon_entropy,
)
from manipulation_bench.scorers.social_deduction import (
    deception_success,
    game_manipulation_detection,
    game_win_rate,
    vote_accuracy,
)
from manipulation_bench.scorers.spread import (
    belief_trajectory,
    resistance_rate,
    spread_rate,
    spread_speed,
)
from manipulation_bench.scorers.voting import juror_voting

__all__ = [
    # Behavioral
    "argument_novelty",
    "backfire_rate",
    "persona_consistency",
    "rhetoric_classification",
    "sycophancy_rate",
    # Dynamics
    "deception_detection_rate",
    "faction_survival_time",
    "influence_asymmetry",
    "opinion_change_rate",
    "time_to_consensus",
    # Grounded
    "ground_truth_persuasion",
    # Judges
    "argument_quality",
    "belief_shift",
    "manipulation_detection",
    # Negotiation
    "agreement_compliance",
    "negotiation_manipulation",
    "territorial_success",
    # Network
    "active_interface_density",
    "clustering_coefficient",
    "echo_chamber_index",
    "opinion_modularity",
    # Opinion
    "bimodality_coefficient",
    "esteban_ray_index",
    "inverse_simpson",
    "mean_absolute_difference",
    "mean_opinion",
    "opinion_spread",
    "shannon_entropy",
    # Social deduction
    "deception_success",
    "game_manipulation_detection",
    "game_win_rate",
    "vote_accuracy",
    # Spread
    "belief_trajectory",
    "resistance_rate",
    "spread_rate",
    "spread_speed",
    # Voting
    "juror_voting",
]
