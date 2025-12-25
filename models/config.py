"""
Model configuration - THE SINGLE PLACE to set which model variation to use.

To change the model, simply update CURRENT_MODEL_CONFIG below.
"""

# ============================================================================
# CURRENT MODEL CONFIGURATION - EDIT THIS TO SWITCH MODELS
# ============================================================================

CURRENT_MODEL_CONFIG = {
    # Balance rule: How to determine if a triangle is balanced
    # Options: ClassicBalanceRule, StrictPositiveBalanceRule, TriangleInequalityRule, ProductBalanceRule
    "balance_rule": "TransitivityBalanceRule",

    # Balance rule parameters (optional, depends on rule)
    "balance_params": {
        # For TriangleInequalityRule:
        # "min_strength": 0.01,
        # "tolerance": 0.001,

        # For ProductBalanceRule:
        # "threshold": 0.001,
        # "min_strength": 0.01,
    },

    # Action strategy: How people respond to unbalanced triangles
    # Options: ClassicActionStrategy, ConservativeActionStrategy, AggressiveActionStrategy,
    #          ProactiveActionStrategy, BalancedActionStrategy
    "action_strategy": "ClassicActionStrategy",

    # Action strategy parameters (optional, depends on strategy)
    "action_params": {
        # For ConservativeActionStrategy:
        # "adjustment_size": 0.2,

        # For ProactiveActionStrategy:
        # "strengthen_amount": 0.3,
    },

    # Relationship type: How edge values are represented
    # Options: DiscreteRelationship, ContinuousRelationship, BipolarRelationship
    "relationship_type": "DiscreteRelationship",

    # Relationship type parameters
    "relationship_params": {
        # For ContinuousRelationship:
        # "min_val": 0.0,
        # "max_val": 1.0,
        # "neutral_threshold": 0.01,

        # For BipolarRelationship:
        # "max_val": 1.0,
        # "neutral_threshold": 0.01,
    },

    # Decay mechanism: How relationships decay over time
    # Options: NoDecay, LinearDecay, ExponentialDecay, AsymmetricDecay
    "decay": "NoDecay",

    # Decay parameters (optional, depends on decay type)
    "decay_params": {
        # For LinearDecay:
        # "rate": 0.01,

        # For ExponentialDecay:
        # "half_life": 50.0,

        # For AsymmetricDecay:
        # "positive_rate": 0.02,
        # "negative_rate": 0.005,
    },
}


# ============================================================================
# PRESET CONFIGURATIONS - Quick model presets you can copy to CURRENT_MODEL_CONFIG
# ============================================================================

PRESET_CONFIGS = {
    "classic": {
        "balance_rule": "ClassicBalanceRule",
        "balance_params": {},
        "action_strategy": "ClassicActionStrategy",
        "action_params": {},
        "relationship_type": "DiscreteRelationship",
        "relationship_params": {},
        "decay": "NoDecay",
        "decay_params": {},
    },

    "continuous_closeness": {
        "balance_rule": "TriangleInequalityRule",
        "balance_params": {"min_strength": 0.1, "tolerance": 0.01},
        "action_strategy": "ConservativeActionStrategy",
        "action_params": {"adjustment_size": 0.15},
        "relationship_type": "ContinuousRelationship",
        "relationship_params": {"min_val": 0.0, "max_val": 1.0, "neutral_threshold": 0.05},
        "decay": "LinearDecay",
        "decay_params": {"rate": 0.01},
    },

    "bipolar_weighted": {
        "balance_rule": "ProductBalanceRule",
        "balance_params": {"threshold": 0.01, "min_strength": 0.05},
        "action_strategy": "ProactiveActionStrategy",
        "action_params": {"strengthen_amount": 0.2},
        "relationship_type": "BipolarRelationship",
        "relationship_params": {"max_val": 1.0, "neutral_threshold": 0.05},
        "decay": "ExponentialDecay",
        "decay_params": {"half_life": 50.0},
    },

    "grudge_model": {
        "balance_rule": "ProductBalanceRule",
        "balance_params": {"threshold": 0.01, "min_strength": 0.05},
        "action_strategy": "BalancedActionStrategy",
        "action_params": {},
        "relationship_type": "BipolarRelationship",
        "relationship_params": {"max_val": 1.0, "neutral_threshold": 0.05},
        "decay": "AsymmetricDecay",
        "decay_params": {"positive_rate": 0.03, "negative_rate": 0.005},
    },
}


# Helper function to switch to a preset
def use_preset(preset_name: str):
    """
    Switch to a preset configuration.

    Usage:
        from models.config import use_preset
        use_preset("continuous_closeness")

    Args:
        preset_name: Name of preset from PRESET_CONFIGS
    """
    global CURRENT_MODEL_CONFIG
    if preset_name in PRESET_CONFIGS:
        CURRENT_MODEL_CONFIG = PRESET_CONFIGS[preset_name].copy()
        print(f"Switched to preset: {preset_name}")
    else:
        print(f"Unknown preset: {preset_name}")
        print(f"Available presets: {list(PRESET_CONFIGS.keys())}")


# Switch to desired preset - edit this line to change models
use_preset("continuous_closeness")
