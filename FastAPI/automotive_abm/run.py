from .model import SupplyChainModel
import matplotlib.pyplot as plt
import pandas as pd

def plot_simulation_results(model, tariff_shock_step=8):
    """Create the original 2x2 visualization plots"""

    steps = len(model.metrics["cost_history"])

    # Calculate production failures by step
    failure_counts = {}
    for step, _ in model.metrics["production_failures"]:
        failure_counts[step] = failure_counts.get(step, 0) + 1

    failure_values = [failure_counts.get(i, 0) for i in range(steps)]

    # Plot results using 2x2 grid
    plt.figure(figsize=(14, 8))

    # Plot 1: Component Cost
    plt.subplot(2, 2, 1)
    plt.plot(model.metrics["cost_history"], marker='o')
    plt.axvline(tariff_shock_step, color='red', linestyle='--', label='Tariff Shock')
    plt.title("Component Cost Over Time")
    plt.xlabel("Time Step")
    plt.ylabel("Cost (USD)")
    plt.legend()
    plt.grid(True)

    # Plot 2: Components Built
    plt.subplot(2, 2, 2)
    plt.plot(model.metrics["components_built"], marker='s')
    plt.axvline(tariff_shock_step, color='red', linestyle='--')
    plt.title("Total Components Built")
    plt.xlabel("Time Step")
    plt.ylabel("Count")
    plt.grid(True)

    # Plot 3: Unused Inventory
    plt.subplot(2, 2, 3)
    plt.plot(model.metrics["unused_inventory"], marker='x')
    plt.axvline(tariff_shock_step, color='red', linestyle='--')
    plt.title("Unused Inventory Over Time")
    plt.xlabel("Time Step")
    plt.ylabel("Units")
    plt.grid(True)

    # Plot 4: Production Failures
    plt.subplot(2, 2, 4)
    plt.bar(range(steps), failure_values, color='orange')
    plt.axvline(tariff_shock_step, color='red', linestyle='--')
    plt.title("Production Failures")
    plt.xlabel("Time Step")
    plt.ylabel("Failures")
    plt.grid(True)

    plt.tight_layout()
    plt.show()


def run_simulation_with_plots(supplier_data, steps=24):
    """Run simulation with DataFrame input and create plots"""

    model = SupplyChainModel(supplier_data=supplier_data, seed=42)

    # Analyze initial supplier setup
    model.analyze_supplier_diversity()

    tariff_shock_step = 8

    for t in range(steps):
        print(f"\n--- Time Step {t} ---")

        if t == tariff_shock_step:
            # Simulate China tariff increase
            model.tariffs['China'] = 0.50
            print("🚨 TRADE WAR: 50% tariff applied to Chinese imports")

        model.step()

        # Print current inventory levels every 5 steps
        if t % 5 == 0:
            print(f"Current inventory levels: {dict(list(model.parts_inventory.items())[:3])}...")

    # Final analysis
    print(f"\n=== SIMULATION COMPLETE ===")
    print(f"Total components built: {model.manufacturer.components_built}")
    print(f"Final component cost: ${model.manufacturer.get_component_cost():.2f}")
    print(f"Total production failures: {len(model.metrics['production_failures'])}")

    # Create visualizations
    plot_simulation_results(model, tariff_shock_step)

    return model


# Example usage
if __name__ == "__main__":
    # Create DataFrame from your brake parts data
    brake_parts_data = {
        'categoryId': [100025, 100026, 100806, 100807, 100028],
        'categoryName': ['Brake Booster', 'Brake Master Cylinder', 'Brake Caliper Parts', 'Brake Caliper Mounting',
                         'Wheel Cylinders'],
        'fullPath': ['Braking System > Brake Booster', 'Braking System > Brake Master Cylinder',
                     'Braking System > Brake Caliper > Brake Caliper...',
                     'Braking System > Brake Caliper > Brake Caliper...', 'Braking System > Wheel Cylinders'],
        'articleNo': [None, 'BMT-155', 'SZ733', '0 986 473 202', 'WCT-039'],
        'supplierName': [None, 'AISIN', 'TRW', 'BOSCH', 'AISIN'],
        'articleProductName': [None, 'Brake Master Cylinder', 'Piston, brake caliper', 'Brake Caliper',
                               'Wheel Brake Cylinder'],
        'estimatedPriceGBP': [70, 45, 12, 85, 18],
        'likelyManufacturingOrigin': ['China', 'Japan', 'Poland', 'Germany', 'Japan']
    }

    df = pd.DataFrame(brake_parts_data)

    # Run simulation with DataFrame and create plots
    model = run_simulation_with_plots(df, steps=24)