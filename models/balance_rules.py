"""
Different rules for determining triangle balance.
"""

from abc import ABC, abstractmethod
from typing import List, Optional


class BalanceRule(ABC):
    """Abstract base class for balance rules."""

    @abstractmethod
    def is_balanced(self, edge_values: List[float]) -> Optional[bool]:
        """
        Check if a triangle is balanced.

        Args:
            edge_values: List of 3 edge values (interpretation depends on relationship type)

        Returns:
            True if balanced, False if unbalanced, None if incomplete
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this balance rule."""
        pass


class ClassicBalanceRule(BalanceRule):
    """
    Classic structural balance theory:
    - Balanced: 3 positive OR 1 positive + 2 negative OR 3 negative
    - Unbalanced: 2 positive + 1 negative

    Assumes discrete types: POSITIVE=1, NEGATIVE=-1, NEUTRAL=0
    """

    def is_balanced(self, edge_values: List[float]) -> Optional[bool]:
        if len(edge_values) != 3:
            return None

        # Count positive and negative edges
        positive_count = sum(1 for v in edge_values if v > 0)
        negative_count = sum(1 for v in edge_values if v < 0)
        neutral_count = sum(1 for v in edge_values if v == 0)

        # Skip triangles with neutral edges - incomplete triangles
        if neutral_count > 0:
            return None

        # Balanced: 3 positive OR 1 positive + 2 negative OR 3 negative
        if positive_count == 3 or (positive_count == 1 and negative_count == 2):
            return True

        return False

    def get_name(self) -> str:
        return "Classic Heider Triangle Balance (+++, +--)"
    

class TransitivityBalanceRule(BalanceRule):
    """
    Classic structural balance theory:
    - Balanced: 3 positive OR 1 positive + 2 negative OR 3 negative
    - Unbalanced: 2 positive + 1 negative

    Assumes discrete types: POSITIVE=1, NEGATIVE=-1, NEUTRAL=0
    """

    def is_balanced(self, edge_values: List[float]) -> Optional[bool]:
        if len(edge_values) != 3:
            return None

        # Count positive and negative edges
        positive_count = sum(1 for v in edge_values if v > 0)
        negative_count = sum(1 for v in edge_values if v < 0)
        neutral_count = sum(1 for v in edge_values if v == 0)

        # Skip triangles with neutral edges - incomplete triangles
        if neutral_count > 0:
            return None

        # Balanced: 3 positive OR 1 positive + 2 negative OR 3 negative
        if positive_count == 3 or (positive_count == 1 and negative_count == 2) or negative_count == 3:
            return True

        return False

    def get_name(self) -> str:
        return "Transitivity Balance  (+++, +--, ---)"



class StrictPositiveBalanceRule(BalanceRule):
    """
    Only triangles with all positive edges are balanced.
    Useful for modeling pure friendship clusters.
    """

    def is_balanced(self, edge_values: List[float]) -> Optional[bool]:
        if len(edge_values) != 3:
            return None

        # All must be positive
        if all(v > 0 for v in edge_values):
            return True

        # If any neutral, incomplete
        if any(v == 0 for v in edge_values):
            return None

        return False

    def get_name(self) -> str:
        return "Strict Positive Balance"


class TriangleInequalityRule(BalanceRule):
    """
    Triangle inequality rule for continuous positive edge weights.

    For positive weights representing closeness/strength (0 to max):
    Balanced if the triangle inequality holds for all three combinations:
    - w_ab + w_bc >= w_ac
    - w_bc + w_ca >= w_ab
    - w_ca + w_ab >= w_bc

    This ensures transitivity: if A is close to B and B is close to C,
    then A should be reasonably close to C.

    Args:
        min_strength: Minimum edge weight to be considered (below this = incomplete triangle)
        tolerance: Small tolerance value for floating point comparisons
    """

    def __init__(self, min_strength: float = 0.01, tolerance: float = 0.001):
        self.min_strength = min_strength
        self.tolerance = tolerance

    def is_balanced(self, edge_values: List[float]) -> Optional[bool]:
        if len(edge_values) != 3:
            return None

        # If any edge is too weak, incomplete triangle
        if any(v < self.min_strength for v in edge_values):
            return None

        # All edges must be positive
        if any(v <= 0 for v in edge_values):
            return None

        w1, w2, w3 = edge_values

        # Check triangle inequality for all three combinations
        # Subtract tolerance to allow for small floating point errors
        ineq1 = (w1 + w2) >= (w3 - self.tolerance)
        ineq2 = (w2 + w3) >= (w1 - self.tolerance)
        ineq3 = (w3 + w1) >= (w2 - self.tolerance)

        # All three must hold for balance
        return ineq1 and ineq2 and ineq3

    def get_name(self) -> str:
        return f"Triangle Inequality (min={self.min_strength})"


class ProductBalanceRule(BalanceRule):
    """
    Balance based on product of edge weights (for bipolar weights -x to +x).

    Based on continuous-time structural balance theory where:
    dx_ij/dt = Σ_k (x_ik × x_kj)

    Product = w_ab × w_bc × w_ca
    - Balanced: Product > threshold (positive product)
    - Unbalanced: Product < -threshold (negative product)

    This naturally extends classic balance:
    - (+)(+)(+) = + → balanced
    - (+)(−)(−) = + → balanced
    - (−)(−)(−) = − → unbalanced
    - (+)(+)(−) = − → unbalanced

    Args:
        threshold: Minimum absolute product value to consider (below = incomplete)
        min_strength: Minimum absolute edge weight (below = incomplete triangle)
    """

    def __init__(self, threshold: float = 0.001, min_strength: float = 0.01):
        self.threshold = threshold
        self.min_strength = min_strength

    def is_balanced(self, edge_values: List[float]) -> Optional[bool]:
        if len(edge_values) != 3:
            return None

        # If any edge is neutral/missing (absolute value too low), incomplete
        if any(abs(v) < self.min_strength for v in edge_values):
            return None

        # Calculate product of edge values
        product = edge_values[0] * edge_values[1] * edge_values[2]

        # Positive product = balanced, negative product = unbalanced
        if product > self.threshold:
            return True
        elif product < -self.threshold:
            return False
        else:
            return None  # Ambiguous (product near zero)

    def get_name(self) -> str:
        return f"Product Balance (threshold={self.threshold})"
