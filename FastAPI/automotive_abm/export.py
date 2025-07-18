import pandas as pd
import os
from datetime import datetime
import numpy as np

def export_simulation_data(model, output_path="key_simulation_data.csv"):
    """
    Export only the key simulation metrics to CSV

    Args:
        model: The simulation model with metrics
        output_path: Path to save the CSV file

    Returns:
        str: Path to the exported CSV file
    """

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    # Build simplified dataset with key metrics only
    key_data = []

    simulation_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    manufacturer_name = model.manufacturer.manufacturer_name
    total_steps = model.current_step

    for step in range(total_steps):
        # Get autogen metrics for this step
        cost = model.metrics["cost_history"][step] if step < len(model.metrics["cost_history"]) else 0
        components_built = model.metrics["components_built"][step] if step < len(
            model.metrics["components_built"]) else 0
        unused_inventory = model.metrics["unused_inventory"][step] if step < len(
            model.metrics["unused_inventory"]) else 0

        # Count production failures for this step
        failures_this_step = len([f for f in model.metrics.get("production_failures", []) if f[0] == step])

        # Calculate components built this step
        components_this_step = 0
        if step > 0:
            prev_built = model.metrics["components_built"][step - 1] if step - 1 < len(
                model.metrics["components_built"]) else 0
            components_this_step = components_built - prev_built

        row = {
            'simulation_id': simulation_id,
            'step': step,
            'timestamp': datetime.now().isoformat(),
            'manufacturer_name': manufacturer_name,
            'total_component_cost_usd': cost,
            'cumulative_components_built': components_built,
            'components_built_this_step': components_this_step,
            'total_unused_inventory': unused_inventory,
            'production_failures_count': failures_this_step,
            'period': 'Pre-Shock' if step < 8 else 'Post-Shock'  # Assuming shock at step 8
        }

        key_data.append(row)

    # Create DataFrame and add some calculated columns
    df = pd.DataFrame(key_data)

    if not df.empty:
        # Add cumulative failures
        df['cumulative_failures'] = df['production_failures_count'].cumsum()

        # Add efficiency metric
        df['inventory_efficiency'] = df['cumulative_components_built'] / (
                    df['total_unused_inventory'] + 1)  # +1 to avoid division by zero


    # Export to CSV
    df.to_csv(output_path, index=False)

    print(f"Exported key simulation data to: {output_path}")
    print(f"Dataset contains {len(df)} rows and {len(df.columns)} columns")
    print(f"Key columns: {list(df.columns)}")

    return output_path

# Usage example:
# After running your simulation:
# export_key_simulation_data(model, "key_metrics.csv")