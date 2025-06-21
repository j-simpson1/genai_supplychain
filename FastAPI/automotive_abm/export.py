def export_simulation_data(model, output_path="simulation_data.csv"):
    """
    Export simulation metrics to CSV for Power BI import

    Args:
        model: The simulation model with metrics
        output_path: Path to save the CSV file
    """
    import pandas as pd
    import os

    # Prepare data for export
    data = {
        'step': list(range(model.current_step)),
        'component_cost': model.metrics["cost_history"],
        'components_built': model.metrics["components_built"],
        'unused_inventory': model.metrics["unused_inventory"]
    }

    # Add inventory data for each part
    inventory_data = model.metrics["inventory_levels"]
    all_part_keys = set()
    for inv in inventory_data:
        all_part_keys.update(inv.keys())

    for part_key in all_part_keys:
        data[f'inventory_{part_key}'] = [inv.get(part_key, 0) for inv in inventory_data]

    # Create production failures data
    failures_by_step = {}
    for step, key in model.metrics["production_failures"]:
        if step not in failures_by_step:
            failures_by_step[step] = 0
        failures_by_step[step] += 1

    data['production_failures'] = [failures_by_step.get(step, 0) for step in range(model.current_step)]

    # Create DataFrame and export
    df = pd.DataFrame(data)

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    # Export to CSV
    df.to_csv(output_path, index=False)

    return output_path