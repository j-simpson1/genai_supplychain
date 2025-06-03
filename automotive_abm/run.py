from agent import ManufacturerAgent
from model import SupplyChainModel

# Simple example function
def run_example():
    """Example usage with Mesa 3.2.0"""

    # Create model
    model = SupplyChainModel(seed=42)

    # Run a few steps to build inventory
    for _ in range(3):
        model.step()

    # Find the manufacturer
    manufacturer = None
    for agent in model.agents:
        if isinstance(agent, ManufacturerAgent):
            manufacturer = agent
            break

    if manufacturer:
        # Analyze 50% tariff on China
        impact = manufacturer.analyze_tariff_impact({'China': 0.50})

        print("Tariff Impact Analysis:")
        print(f"Total potential savings: ${impact['total_potential_savings']:.2f}")

        for part, details in impact['affected_parts'].items():
            print(f"\n{part}:")
            print(f"  Current: {details['current']} - ${details['current_cost']:.2f}")
            print(f"  Alternative: {details['alternative']} - ${details['alternative_cost']:.2f}")
            print(f"  Savings: ${details['savings']:.2f}")


if __name__ == "__main__":
    run_example()