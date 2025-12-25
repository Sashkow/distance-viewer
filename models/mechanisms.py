"""
Additional mechanisms: relationship decay.
"""

from abc import ABC, abstractmethod


class DecayMechanism(ABC):
    """Abstract base class for relationship decay over time."""

    @abstractmethod
    def apply_decay(self, edge_value: float, relationship_type: 'RelationshipType') -> float:
        """
        Apply decay to an edge value.

        Args:
            edge_value: Current edge value
            relationship_type: The relationship type system

        Returns:
            New decayed value
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this decay mechanism."""
        pass


class NoDecay(DecayMechanism):
    """No decay - relationships remain constant."""

    def apply_decay(self, edge_value: float, relationship_type: 'RelationshipType') -> float:
        return edge_value

    def get_name(self) -> str:
        return "No Decay"


class LinearDecay(DecayMechanism):
    """
    Linear decay toward neutral/zero.
    Positive relationships weaken, negative relationships weaken.
    """

    def __init__(self, rate: float = 0.01):
        self.rate = rate

    def apply_decay(self, edge_value: float, relationship_type: 'RelationshipType') -> float:
        # Move toward zero
        if edge_value > 0:
            new_value = edge_value - self.rate
            return max(0, new_value)
        elif edge_value < 0:
            new_value = edge_value + self.rate
            return min(0, new_value)
        return edge_value

    def get_name(self) -> str:
        return f"Linear Decay (rate={self.rate})"


class ExponentialDecay(DecayMechanism):
    """
    Exponential decay toward neutral/zero.
    Stronger relationships decay more slowly (in absolute terms).
    """

    def __init__(self, half_life: float = 50.0):
        """
        Args:
            half_life: Number of iterations for relationship to reach half strength
        """
        self.half_life = half_life
        self.decay_factor = 0.5 ** (1.0 / half_life)

    def apply_decay(self, edge_value: float, relationship_type: 'RelationshipType') -> float:
        # Multiply by decay factor (preserves sign)
        new_value = edge_value * self.decay_factor

        # If very close to zero, snap to zero
        if abs(new_value) < 0.001:
            return 0.0

        return new_value

    def get_name(self) -> str:
        return f"Exponential Decay (half_life={self.half_life})"


class AsymmetricDecay(DecayMechanism):
    """
    Asymmetric decay: positive relationships decay, negative relationships persist.
    Models grudges lasting longer than friendships.
    """

    def __init__(self, positive_rate: float = 0.02, negative_rate: float = 0.005):
        self.positive_rate = positive_rate
        self.negative_rate = negative_rate

    def apply_decay(self, edge_value: float, relationship_type: 'RelationshipType') -> float:
        if edge_value > 0:
            # Positive decays faster
            new_value = edge_value - self.positive_rate
            return max(0, new_value)
        elif edge_value < 0:
            # Negative decays slower (grudges persist)
            new_value = edge_value + self.negative_rate
            return min(0, new_value)
        return edge_value

    def get_name(self) -> str:
        return f"Asymmetric Decay (pos={self.positive_rate}, neg={self.negative_rate})"


# Placeholder for future random events
class RandomEventGenerator(ABC):
    """Abstract base class for random events (not yet implemented)."""

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this event generator."""
        pass


class NoEvents(RandomEventGenerator):
    """No random events."""

    def get_name(self) -> str:
        return "No Events"
