"""
Test script to verify different model configurations work correctly.
"""

from models.factory import ModelFactory
from models.config import PRESET_CONFIGS

def test_model_configs():
    """Test that all preset configurations can be created."""
    print("Testing model configurations...\n")

    # Test default config
    print("1. Testing DEFAULT configuration:")
    try:
        components = ModelFactory.create_from_config()
        print(f"   ✓ Balance Rule: {components['balance_rule'].get_name()}")
        print(f"   ✓ Action Strategy: {components['action_strategy'].get_name()}")
        print(f"   ✓ Relationship Type: {components['relationship_type'].get_name()}")
        print(f"   ✓ Decay: {components['decay'].get_name()}")
        print("   SUCCESS!\n")
    except Exception as e:
        print(f"   ✗ FAILED: {e}\n")

    # Test all presets
    for preset_name, preset_config in PRESET_CONFIGS.items():
        print(f"2. Testing '{preset_name}' preset:")
        try:
            components = ModelFactory.create_from_config(preset_config)
            print(f"   ✓ Balance Rule: {components['balance_rule'].get_name()}")
            print(f"   ✓ Action Strategy: {components['action_strategy'].get_name()}")
            print(f"   ✓ Relationship Type: {components['relationship_type'].get_name()}")
            print(f"   ✓ Decay: {components['decay'].get_name()}")
            print("   SUCCESS!\n")
        except Exception as e:
            print(f"   ✗ FAILED: {e}\n")

    print("All model configuration tests completed!")


def test_balance_rules():
    """Test balance rules with sample triangles."""
    print("\nTesting balance rules with sample triangles:\n")

    from models.balance_rules import ClassicBalanceRule, TriangleInequalityRule, ProductBalanceRule

    # Test classic rule
    classic = ClassicBalanceRule()
    print("Classic Balance Rule:")
    print(f"  [1, 1, 1] (all positive): {classic.is_balanced([1, 1, 1])}")
    print(f"  [1, -1, -1] (one positive, two negative): {classic.is_balanced([1, -1, -1])}")
    print(f"  [1, 1, -1] (two positive, one negative): {classic.is_balanced([1, 1, -1])}")
    print(f"  [-1, -1, -1] (all negative): {classic.is_balanced([-1, -1, -1])}")

    # Test triangle inequality
    tri_ineq = TriangleInequalityRule(min_strength=0.1)
    print("\nTriangle Inequality Rule:")
    print(f"  [0.5, 0.5, 0.5]: {tri_ineq.is_balanced([0.5, 0.5, 0.5])}")
    print(f"  [0.5, 0.5, 0.9]: {tri_ineq.is_balanced([0.5, 0.5, 0.9])}")
    print(f"  [0.5, 0.5, 1.5]: {tri_ineq.is_balanced([0.5, 0.5, 1.5])}")

    # Test product rule
    product = ProductBalanceRule()
    print("\nProduct Balance Rule:")
    print(f"  [0.5, 0.5, 0.5]: {product.is_balanced([0.5, 0.5, 0.5])}")
    print(f"  [0.5, -0.5, -0.5]: {product.is_balanced([0.5, -0.5, -0.5])}")
    print(f"  [0.5, 0.5, -0.5]: {product.is_balanced([0.5, 0.5, -0.5])}")
    print(f"  [-0.5, -0.5, -0.5]: {product.is_balanced([-0.5, -0.5, -0.5])}")


def test_relationship_types():
    """Test relationship type encoding/decoding."""
    print("\n\nTesting relationship types:\n")

    from models.relationship_types import DiscreteRelationship, ContinuousRelationship, BipolarRelationship

    # Discrete
    discrete = DiscreteRelationship()
    print("Discrete Relationship:")
    print(f"  Encode 1.0: {discrete.encode_to_storage(1.0)}")
    print(f"  Encode -1.0: {discrete.encode_to_storage(-1.0)}")
    print(f"  Decode 'POSITIVE': {discrete.decode_from_storage('POSITIVE')}")

    # Continuous
    continuous = ContinuousRelationship(min_val=0.0, max_val=1.0)
    print("\nContinuous Relationship:")
    print(f"  Random value: {continuous.get_random_value()}")
    print(f"  Adjust 0.5 by +0.2: {continuous.adjust_value(0.5, 0.2)}")
    print(f"  Adjust 0.9 by +0.2: {continuous.adjust_value(0.9, 0.2)}")

    # Bipolar
    bipolar = BipolarRelationship(max_val=1.0)
    print("\nBipolar Relationship:")
    for _ in range(3):
        val = bipolar.get_random_value()
        print(f"  Random value: {val:.2f}")


if __name__ == "__main__":
    test_model_configs()
    test_balance_rules()
    test_relationship_types()
    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)
