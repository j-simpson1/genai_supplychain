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

    # Plot results
    plt.figure(figsize=(12, 4))

    # Plot 1: Component Cost
    plt.subplot(1, 3, 1)
    plt.plot(model.metrics["cost_history"], marker='o')
    plt.axvline(tariff_shock_step, color='red', linestyle='--', label='Tariff Shock')
    plt.title("Component Cost Over Time")
    plt.xlabel("Time Step")
    plt.ylabel("Cost (USD)")
    plt.legend()

    # Plot 2: Components Built
    plt.subplot(1, 3, 2)
    plt.plot(model.metrics["components_built"], marker='s')
    plt.axvline(tariff_shock_step, color='red', linestyle='--')
    plt.title("Total Components Built")
    plt.xlabel("Time Step")
    plt.ylabel("Count")

    # Plot 3: Unused Inventory
    plt.subplot(1, 3, 3)
    plt.plot(model.metrics["unused_inventory"], marker='x')
    plt.axvline(tariff_shock_step, color='red', linestyle='--')
    plt.title("Unused Inventory Over Time")
    plt.xlabel("Time Step")
    plt.ylabel("Units")

    for ax in plt.gcf().get_axes():
        ax.grid(True)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    run_simulation(steps=12)