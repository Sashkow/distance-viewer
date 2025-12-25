"""
Factory for creating model instances from configuration.
Auto-generates class registry from imported modules.
"""

from typing import Dict, Any
import inspect
from . import balance_rules
from . import action_strategies
from . import relationship_types
from . import mechanisms
from .config import CURRENT_MODEL_CONFIG


class ModelFactory:
    """Factory for creating model components from configuration using class names."""

    # Auto-generate registries from module contents
    @staticmethod
    def _build_registry(module, base_class):
        """Build a registry of classes from a module that inherit from base_class."""
        registry = {}
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Only include classes defined in this module (not imports) that inherit from base_class
            if obj.__module__ == module.__name__ and issubclass(obj, base_class) and obj != base_class:
                registry[name] = obj
        return registry

    # Registries are auto-generated - add new classes to the modules and they appear here automatically
    BALANCE_RULES = _build_registry.__func__(balance_rules, balance_rules.BalanceRule)
    ACTION_STRATEGIES = _build_registry.__func__(action_strategies, action_strategies.ActionStrategy)
    RELATIONSHIP_TYPES = _build_registry.__func__(relationship_types, relationship_types.RelationshipType)
    DECAY_MECHANISMS = _build_registry.__func__(mechanisms, mechanisms.DecayMechanism)

    @staticmethod
    def create_balance_rule(config: Dict[str, Any]) -> balance_rules.BalanceRule:
        """Create a balance rule from configuration using class name."""
        class_name = config.get("balance_rule", "ClassicBalanceRule")
        params = config.get("balance_params", {})

        if class_name not in ModelFactory.BALANCE_RULES:
            raise ValueError(f"Unknown balance rule: {class_name}. Available: {list(ModelFactory.BALANCE_RULES.keys())}")

        return ModelFactory.BALANCE_RULES[class_name](**params)

    @staticmethod
    def create_action_strategy(config: Dict[str, Any]) -> action_strategies.ActionStrategy:
        """Create an action strategy from configuration using class name."""
        class_name = config.get("action_strategy", "ClassicActionStrategy")
        params = config.get("action_params", {})

        if class_name not in ModelFactory.ACTION_STRATEGIES:
            raise ValueError(f"Unknown action strategy: {class_name}. Available: {list(ModelFactory.ACTION_STRATEGIES.keys())}")

        return ModelFactory.ACTION_STRATEGIES[class_name](**params)

    @staticmethod
    def create_relationship_type(config: Dict[str, Any]) -> relationship_types.RelationshipType:
        """Create a relationship type from configuration using class name."""
        class_name = config.get("relationship_type", "DiscreteRelationship")
        params = config.get("relationship_params", {})

        if class_name not in ModelFactory.RELATIONSHIP_TYPES:
            raise ValueError(f"Unknown relationship type: {class_name}. Available: {list(ModelFactory.RELATIONSHIP_TYPES.keys())}")

        return ModelFactory.RELATIONSHIP_TYPES[class_name](**params)

    @staticmethod
    def create_decay_mechanism(config: Dict[str, Any]) -> mechanisms.DecayMechanism:
        """Create a decay mechanism from configuration using class name."""
        class_name = config.get("decay", "NoDecay")
        params = config.get("decay_params", {})

        if class_name not in ModelFactory.DECAY_MECHANISMS:
            raise ValueError(f"Unknown decay type: {class_name}. Available: {list(ModelFactory.DECAY_MECHANISMS.keys())}")

        return ModelFactory.DECAY_MECHANISMS[class_name](**params)

    @staticmethod
    def create_from_config(config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create all model components from a configuration dict.

        Args:
            config: Configuration dictionary (uses CURRENT_MODEL_CONFIG if None)

        Returns:
            Dictionary with all model components
        """
        if config is None:
            config = CURRENT_MODEL_CONFIG

        return {
            "balance_rule": ModelFactory.create_balance_rule(config),
            "action_strategy": ModelFactory.create_action_strategy(config),
            "relationship_type": ModelFactory.create_relationship_type(config),
            "decay": ModelFactory.create_decay_mechanism(config),
        }

    @staticmethod
    def get_model_description(config: Dict[str, Any] = None) -> str:
        """
        Get a human-readable description of the model configuration.

        Args:
            config: Configuration dictionary (uses CURRENT_MODEL_CONFIG if None)

        Returns:
            Description string
        """
        if config is None:
            config = CURRENT_MODEL_CONFIG

        components = ModelFactory.create_from_config(config)

        description = "Model Configuration:\n"
        description += f"  Balance Rule: {components['balance_rule'].get_name()}\n"
        description += f"  Action Strategy: {components['action_strategy'].get_name()}\n"
        description += f"  Relationship Type: {components['relationship_type'].get_name()}\n"
        description += f"  Decay: {components['decay'].get_name()}\n"

        return description
