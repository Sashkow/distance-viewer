"""
Different action strategies for how people respond to unbalanced triangles.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
import random


# Action type definitions with their execution logic
class ActionType:
    """Defines available action types and their logic."""

    @staticmethod
    def change_edge_random(person_id: int, triangle: Dict, relationship_type: 'RelationshipType') -> Dict[str, Any]:
        """Change one random edge in triangle to a random new value."""
        edges = [
            (triangle["n1"], triangle["n2"], triangle["e1"]),
            (triangle["n2"], triangle["n3"], triangle["e2"]),
            (triangle["n3"], triangle["n1"], triangle["e3"])
        ]
        person1, person2, current_value = random.choice(edges)
        new_value = relationship_type.get_random_value(exclude=current_value)

        return {
            "type": "change_edge",
            "person1": person1,
            "person2": person2,
            "old_value": current_value,
            "new_value": new_value
        }

    @staticmethod
    def change_edge_adjust(person_id: int, triangle: Dict, relationship_type: 'RelationshipType',
                          adjustment: float = 0.2) -> Dict[str, Any]:
        """Make small adjustment to one random edge in triangle."""
        edges = [
            (triangle["n1"], triangle["n2"], triangle["e1"]),
            (triangle["n2"], triangle["n3"], triangle["e2"]),
            (triangle["n3"], triangle["n1"], triangle["e3"])
        ]
        person1, person2, current_value = random.choice(edges)
        new_value = relationship_type.adjust_value(current_value, adjustment)

        return {
            "type": "change_edge",
            "person1": person1,
            "person2": person2,
            "old_value": current_value,
            "new_value": new_value
        }

    @staticmethod
    def change_edge_strengthen_positive(person_id: int, triangle: Dict, relationship_type: 'RelationshipType',
                                       amount: float = 0.3) -> Dict[str, Any]:
        """Strengthen positive edges or weaken negative edges in triangle."""
        edges = [
            (triangle["n1"], triangle["n2"], triangle["e1"]),
            (triangle["n2"], triangle["n3"], triangle["e2"]),
            (triangle["n3"], triangle["n1"], triangle["e3"])
        ]
        person1, person2, current_value = random.choice(edges)

        # Strengthen if positive, move toward zero/positive if negative
        new_value = relationship_type.adjust_value(current_value, amount)

        return {
            "type": "change_edge",
            "person1": person1,
            "person2": person2,
            "old_value": current_value,
            "new_value": new_value
        }

    @staticmethod
    def create_edge_random(person_id: int, neighbors_of_neighbors: List[Dict],
                          relationship_type: 'RelationshipType') -> Optional[Dict[str, Any]]:
        """Create new edge to a random neighbor's neighbor."""
        if not neighbors_of_neighbors:
            return None

        target = random.choice(neighbors_of_neighbors)
        new_value = relationship_type.get_random_value()

        return {
            "type": "create_edge",
            "person1": person_id,
            "person2": target["id"],
            "new_value": new_value
        }

    @staticmethod
    def delete_edge_weak(person_id: int, triangle: Dict, relationship_type: 'RelationshipType',
                        threshold: float = 0.2) -> Optional[Dict[str, Any]]:
        """Delete the weakest edge in triangle if below threshold."""
        edges = [
            (triangle["n1"], triangle["n2"], triangle["e1"]),
            (triangle["n2"], triangle["n3"], triangle["e2"]),
            (triangle["n3"], triangle["n1"], triangle["e3"])
        ]

        # Find weakest edge
        weakest = min(edges, key=lambda e: abs(e[2]))
        person1, person2, current_value = weakest

        if abs(current_value) < threshold:
            return {
                "type": "delete_edge",
                "person1": person1,
                "person2": person2,
                "old_value": current_value
            }
        return None


class ActionStrategy(ABC):
    """Abstract base class for action strategies."""

    @abstractmethod
    def select_action(
        self,
        person_id: int,
        unbalanced_triangles: List[Dict],
        neighbors_of_neighbors: List[Dict],
        relationship_type: 'RelationshipType'
    ) -> Optional[Dict[str, Any]]:
        """
        Select an action for a person to take.

        Args:
            person_id: ID of the person taking action
            unbalanced_triangles: List of unbalanced triangles the person is in
            neighbors_of_neighbors: List of potential new connections
            relationship_type: The relationship type system in use

        Returns:
            Dictionary describing the action to take, or None if no action
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this action strategy."""
        pass


class ProbabilisticActionStrategy(ActionStrategy):
    """
    Generic probabilistic action strategy.
    Actions are selected based on weighted probabilities.

    Args:
        action_config: List of (action_fn, weight, kwargs) tuples
        name: Name for this strategy
    """

    def __init__(self, action_config: List[tuple], name: str = "Probabilistic"):
        self.action_config = action_config
        self.name = name

    def select_action(
        self,
        person_id: int,
        unbalanced_triangles: List[Dict],
        neighbors_of_neighbors: List[Dict],
        relationship_type: 'RelationshipType'
    ) -> Optional[Dict[str, Any]]:

        if not unbalanced_triangles:
            return None

        # Build weighted choices
        actions = []
        weights = []

        for action_fn, weight, kwargs in self.action_config:
            actions.append((action_fn, kwargs))
            weights.append(weight)

        # Normalize weights to probabilities
        total = sum(weights)
        if total == 0:
            return None
        probabilities = [w / total for w in weights]

        # Select action based on probability distribution
        action_fn, kwargs = random.choices(actions, weights=probabilities)[0]

        # Execute the action
        triangle = random.choice(unbalanced_triangles)

        # Different action types need different arguments
        if action_fn.__name__.startswith('create_edge'):
            result = action_fn(person_id, neighbors_of_neighbors, relationship_type, **kwargs)
        elif action_fn.__name__.startswith('change_edge') or action_fn.__name__.startswith('delete_edge'):
            result = action_fn(person_id, triangle, relationship_type, **kwargs)
        else:
            result = None

        return result

    def get_name(self) -> str:
        return self.name


# Pre-configured strategies using the probabilistic framework

class ClassicActionStrategy(ProbabilisticActionStrategy):
    """Classic: 50% change edge, 50% create edge."""

    def __init__(self):
        config = [
            (ActionType.change_edge_random, 1, {}),
            # (ActionType.create_edge_random, 0.5, {})
        ]
        super().__init__(config, "Classic Actions (change random edge)")


class ConservativeActionStrategy(ProbabilisticActionStrategy):
    """Conservative: Only small adjustments to existing edges."""

    def __init__(self, adjustment_size: float = 0.2):
        config = [
            (ActionType.change_edge_adjust, 1.0, {"adjustment": adjustment_size})
        ]
        super().__init__(config, f"Conservative (adj={adjustment_size})")


class AggressiveActionStrategy(ProbabilisticActionStrategy):
    """Aggressive: 70% create edges, 30% change edges."""

    def __init__(self):
        config = [
            (ActionType.create_edge_random, 0.7, {}),
            (ActionType.change_edge_random, 0.3, {})
        ]
        super().__init__(config, "Aggressive Actions")


class ProactiveActionStrategy(ProbabilisticActionStrategy):
    """Proactive: Strengthen positive relationships."""

    def __init__(self, strengthen_amount: float = 0.3):
        config = [
            (ActionType.change_edge_strengthen_positive, 1.0, {"amount": strengthen_amount})
        ]
        super().__init__(config, f"Proactive (strengthen={strengthen_amount})")


class BalancedActionStrategy(ProbabilisticActionStrategy):
    """Balanced: Mix of all action types."""

    def __init__(self):
        config = [
            (ActionType.change_edge_random, 0.3, {}),
            (ActionType.change_edge_adjust, 0.3, {"adjustment": 0.2}),
            (ActionType.create_edge_random, 0.3, {}),
            (ActionType.delete_edge_weak, 0.1, {"threshold": 0.2})
        ]
        super().__init__(config, "Balanced Actions")
