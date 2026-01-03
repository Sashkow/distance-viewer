"""
Different relationship type systems (discrete vs continuous).
"""

from abc import ABC, abstractmethod
import random
from typing import Optional, Any


class RelationshipType(ABC):
    """Abstract base class for relationship type systems."""

    @abstractmethod
    def get_random_value(self, exclude: Optional[float] = None) -> float:
        """
        Get a random relationship value.

        Args:
            exclude: Optional value to exclude from random selection

        Returns:
            Random relationship value
        """
        pass

    @abstractmethod
    def adjust_value(self, current_value: float, adjustment: float) -> float:
        """
        Adjust a relationship value by some amount.

        Args:
            current_value: Current relationship value
            adjustment: Amount to adjust (interpretation depends on type)

        Returns:
            New adjusted value
        """
        pass

    @abstractmethod
    def encode_to_storage(self, value: float) -> Any:
        """
        Encode relationship value for database storage.

        Args:
            value: Relationship value

        Returns:
            Value suitable for database storage (e.g., "POSITIVE", numeric)
        """
        pass

    @abstractmethod
    def decode_from_storage(self, stored_value: Any) -> float:
        """
        Decode relationship value from database storage.

        Args:
            stored_value: Value from database

        Returns:
            Numeric relationship value for calculations
        """
        pass

    @abstractmethod
    def is_neutral(self, value: float) -> bool:
        """
        Check if a value represents a neutral/missing relationship.

        Args:
            value: Relationship value

        Returns:
            True if neutral/missing
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this relationship type."""
        pass

    @abstractmethod
    def get_range(self) -> tuple:
        """Return the (min, max) range of valid values."""
        pass

    @abstractmethod
    def is_continuous(self) -> bool:
        """Return True if this is a continuous (distance-based) relationship type."""
        pass


class DiscreteRelationship(RelationshipType):
    """
    Classic discrete relationship types: POSITIVE, NEGATIVE, NEUTRAL.
    Encoded as: POSITIVE=1, NEGATIVE=-1, NEUTRAL=0
    """

    def get_random_value(self, exclude: Optional[float] = None) -> float:
        values = [1.0, -1.0, 0.0]
        if exclude is not None:
            values = [v for v in values if v != exclude]
        return random.choice(values)

    def adjust_value(self, current_value: float, adjustment: float) -> float:
        # For discrete, adjustment flips the sign or randomizes
        # Positive adjustment means move toward positive
        if adjustment > 0:
            return 1.0 if current_value <= 0 else -1.0
        else:
            return -1.0 if current_value >= 0 else 1.0

    def encode_to_storage(self, value: float) -> str:
        if value > 0:
            return "POSITIVE"
        elif value < 0:
            return "NEGATIVE"
        else:
            return "NEUTRAL"

    def decode_from_storage(self, stored_value: Any) -> float:
        if isinstance(stored_value, str):
            if stored_value == "POSITIVE":
                return 1.0
            elif stored_value == "NEGATIVE":
                return -1.0
            else:
                return 0.0
        return float(stored_value)

    def is_neutral(self, value: float) -> bool:
        return value == 0.0

    def get_name(self) -> str:
        return "Discrete (Positive/Negative/Neutral)"

    def get_range(self) -> tuple:
        return (-1.0, 1.0)

    def is_continuous(self) -> bool:
        return False


class ContinuousRelationship(RelationshipType):
    """
    Continuous relationship values in range [0, max].
    Represents strength/closeness (all positive).

    NOTE: For continuous values, we store type as "POSITIVE" in Neo4j
    and the actual numeric value should be stored as a 'value' property.
    This is because Neo4j queries filter on type strings.
    """

    def __init__(self, min_val: float = 0.0, max_val: float = 1.0, neutral_threshold: float = 0.01):
        self.min_val = min_val
        self.max_val = max_val
        self.neutral_threshold = neutral_threshold

    def get_random_value(self, exclude: Optional[float] = None) -> float:
        # Bimodal distribution to create triangle inequality violations
        # With DISTANCE_SCALE=300: short edges = 30-90px, long edges = 180-270px
        # This creates triangles where short + short < long (violating inequality)
        if random.random() < 0.5:
            # Short edges: 0.1-0.3 -> 30-90 pixels
            value = random.uniform(0.1, 0.3)
        else:
            # Long edges: 0.6-0.9 -> 180-270 pixels
            value = random.uniform(0.6, 0.9)
        return value

    def adjust_value(self, current_value: float, adjustment: float) -> float:
        # Adjustment adds to current value (clamped to range)
        new_value = current_value + adjustment
        return max(self.min_val, min(self.max_val, new_value))

    def encode_to_storage(self, value: float) -> str:
        # For continuous values, we still need a type string for Neo4j
        # Store as "POSITIVE" since continuous is positive-only
        # The actual numeric value should be stored as a 'value' property
        if abs(value) < self.neutral_threshold:
            return "NEUTRAL"
        else:
            return "POSITIVE"

    def decode_from_storage(self, stored_value: Any) -> float:
        if isinstance(stored_value, str):
            # Legacy compatibility: convert old discrete types
            if stored_value == "POSITIVE":
                return self.max_val
            elif stored_value == "NEGATIVE":
                return self.min_val
            else:
                return 0.0
        return float(stored_value)

    def is_neutral(self, value: float) -> bool:
        return abs(value) < self.neutral_threshold

    def get_name(self) -> str:
        return f"Continuous [{self.min_val}, {self.max_val}]"

    def get_range(self) -> tuple:
        return (self.min_val, self.max_val)

    def is_continuous(self) -> bool:
        return True


class BipolarRelationship(RelationshipType):
    """
    Continuous bipolar relationship values in range [-max, +max].
    Negative = enmity/distance, Positive = friendship/closeness.

    NOTE: For bipolar values, we store type as "POSITIVE" or "NEGATIVE" in Neo4j
    and the actual numeric value should be stored as a 'value' property.
    This is because Neo4j queries filter on type strings.
    """

    def __init__(self, max_val: float = 1.0, neutral_threshold: float = 0.01):
        self.max_val = max_val
        self.min_val = -max_val
        self.neutral_threshold = neutral_threshold

    def get_random_value(self, exclude: Optional[float] = None) -> float:
        # Generate random value, avoiding neutral zone
        if random.random() < 0.5:
            # Positive value
            value = random.uniform(self.neutral_threshold, self.max_val)
        else:
            # Negative value
            value = random.uniform(self.min_val, -self.neutral_threshold)
        return value

    def adjust_value(self, current_value: float, adjustment: float) -> float:
        # Positive adjustment moves toward positive, negative toward negative
        new_value = current_value + adjustment
        return max(self.min_val, min(self.max_val, new_value))

    def encode_to_storage(self, value: float) -> str:
        # For bipolar values, we still need a type string for Neo4j
        # The actual numeric value should be stored as a 'value' property
        if abs(value) < self.neutral_threshold:
            return "NEUTRAL"
        elif value > 0:
            return "POSITIVE"
        else:
            return "NEGATIVE"

    def decode_from_storage(self, stored_value: Any) -> float:
        if isinstance(stored_value, str):
            # Legacy compatibility: convert old discrete types
            if stored_value == "POSITIVE":
                return self.max_val
            elif stored_value == "NEGATIVE":
                return self.min_val
            else:
                return 0.0
        return float(stored_value)

    def is_neutral(self, value: float) -> bool:
        return abs(value) < self.neutral_threshold

    def get_name(self) -> str:
        return f"Bipolar [-{self.max_val}, +{self.max_val}]"

    def get_range(self) -> tuple:
        return (self.min_val, self.max_val)

    def is_continuous(self) -> bool:
        return True
