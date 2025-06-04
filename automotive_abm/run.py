from agent import ManufacturerAgent
from model import SupplyChainModel
import matplotlib.pyplot as plt


def run_simulation(steps=10):
    model = SupplyChainModel(seed=42)

    cost_history = []
    tariff_shock_step = 5

    for t in range(steps):
        print(f"\n--- Time Step {t} ---")

        # Optional dynamic tariff change
        if t == tariff_shock_step:
            model.tariffs['Mexico'] = 0.50
            print("Tariff shock applied: 50% on Mexican imports")

        # Step the model
        model.step()

        # Record cost
        cost = model.manufacturer.get_component_cost()
        cost_history.append(cost)

    # Plotting
    plt.plot(cost_history, marker='o')
    plt.axvline(tariff_shock_step, color='red', linestyle='--', label='Tariff Shock')
    plt.title("Component Cost Over Time")
    plt.xlabel("Time Step")
    plt.ylabel("Component Cost (USD)")
    plt.legend()
    plt.grid(True)
    plt.show()

    return cost_history


if __name__ == "__main__":
    run_simulation(steps=12)