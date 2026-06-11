"""Autonomy configuration — three independently configurable dimensions."""

from dataclasses import dataclass, field


@dataclass
class AutonomyConfig:
    milestone_granularity: str = "chapter"      # chapter | volume | act
    intervention_threshold: str = "conflict_only"  # all | conflict_only | never
    write_mode: str = "draft"                   # suggest | draft | direct
    timeout_action: str = "downgrade_and_continue"  # skip | abort_task | downgrade_and_continue
    max_rewrite_rounds: int = 3
    token_budget: int = 100_000
    confirm_timeout_s: int = 300
    intervention_conditions: dict = field(default_factory=lambda: {
        "setting_conflicts": True,
        "low_score_threshold": 2.5,
        "propose_new_setting": True,
    })

    def to_dict(self) -> dict:
        return {
            "milestone_granularity": self.milestone_granularity,
            "intervention_threshold": self.intervention_threshold,
            "write_mode": self.write_mode,
            "timeout_action": self.timeout_action,
            "max_rewrite_rounds": self.max_rewrite_rounds,
            "token_budget": self.token_budget,
            "confirm_timeout_s": self.confirm_timeout_s,
            "intervention_conditions": self.intervention_conditions,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AutonomyConfig":
        return cls(
            milestone_granularity=d.get("milestone_granularity", "chapter"),
            intervention_threshold=d.get("intervention_threshold", "conflict_only"),
            write_mode=d.get("write_mode", "draft"),
            timeout_action=d.get("timeout_action", "downgrade_and_continue"),
            max_rewrite_rounds=d.get("max_rewrite_rounds", 3),
            token_budget=d.get("token_budget", 100_000),
            confirm_timeout_s=d.get("confirm_timeout_s", 300),
            intervention_conditions=d.get("intervention_conditions", {
                "setting_conflicts": True,
                "low_score_threshold": 2.5,
                "propose_new_setting": True,
            }),
        )
