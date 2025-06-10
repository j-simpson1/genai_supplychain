from agent import ManufacturerAgent
from model import SupplyChainModel
import matplotlib.pyplot as plt


def run_simulation(steps=10):
    model = SupplyChainModel(seed=42)
    tariff_shock_step = 5

    for t in range(steps):
        print(f"\n--- Time Step {t} ---")

        if t == tariff_shock_step:
            model.tariffs['Mexico'] = 0.50
            print("Tariff shock applied: 50% on Mexican imports")

        model.step()

    failure_counts = {}
    for step, _ in model.metrics["production_failures"]:
        failure_counts[step] = failure_counts.get(step, 0) + 1

    steps_with_failures = sorted(failure_counts.keys())
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


if __name__ == "__main__":
    run_simulation(steps=24)