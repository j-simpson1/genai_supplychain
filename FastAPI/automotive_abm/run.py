from FastAPI.automotive_abm.model import EnhancedSupplyChainModel
import matplotlib.pyplot as plt
import numpy as np
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import text


def plot_enhanced_simulation_results(model, scenario_steps=None):
    """Create enhanced visualization plots for simulation results with scenarios"""
    steps = len(model.metrics["cost_history"])

    if scenario_steps is None:
        scenario_steps = {}

    # Calculate production failures by step
    failure_counts = {}
    for step, _ in model.metrics["production_failures"]:
        failure_counts[step] = failure_counts.get(step, 0) + 1
    failure_values = [failure_counts.get(i, 0) for i in range(steps)]

    # Create 2x3 plot grid for enhanced metrics
    plt.figure(figsize=(18, 12))

    # Plot 1: Component Cost with scenarios
    plt.subplot(2, 3, 1)
    costs = model.metrics["cost_history"]
    # Handle infinite costs for plotting
    plot_costs = [c if c != float('inf') else None for c in costs]
    plt.plot(plot_costs, marker='o', linewidth=2)

    # Add scenario markers
    colors = ['red', 'orange', 'purple', 'brown', 'pink']
    for i, (scenario_type, step) in enumerate(scenario_steps.items()):
        if step < steps:
            plt.axvline(step, color=colors[i % len(colors)], linestyle='--',
                        label=f'{scenario_type.replace("_", " ").title()}', alpha=0.7)

    plt.title("Component Cost Over Time", fontsize=14, fontweight='bold')
    plt.xlabel("Time Step")
    plt.ylabel("Cost (USD)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    # Plot 2: Components Built
    plt.subplot(2, 3, 2)
    plt.plot(model.metrics["components_built"], marker='s', color='green', linewidth=2)
    for i, (scenario_type, step) in enumerate(scenario_steps.items()):
        if step < steps:
            plt.axvline(step, color=colors[i % len(colors)], linestyle='--', alpha=0.7)
    plt.title("Total Components Built", fontsize=14, fontweight='bold')
    plt.xlabel("Time Step")
    plt.ylabel("Count")
    plt.grid(True, alpha=0.3)

    # Plot 3: FX Rates Over Time
    plt.subplot(2, 3, 3)
    fx_history = model.metrics["fx_rates_history"]
    if fx_history:
        countries_to_plot = ['China', 'Germany', 'Japan']  # Key countries
        for country in countries_to_plot:
            if country in fx_history[0]:
                fx_values = [step_rates.get(country, 1.0) for step_rates in fx_history]
                plt.plot(fx_values, label=country, linewidth=2)

        for i, (scenario_type, step) in enumerate(scenario_steps.items()):
            if step < steps:
                plt.axvline(step, color=colors[i % len(colors)], linestyle='--', alpha=0.7)

    plt.title("FX Rates Over Time", fontsize=14, fontweight='bold')
    plt.xlabel("Time Step")
    plt.ylabel("FX Rate (vs USD)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    # Plot 4: Unused Inventory
    plt.subplot(2, 3, 4)
    plt.plot(model.metrics["unused_inventory"], marker='x', color='orange', linewidth=2)
    for i, (scenario_type, step) in enumerate(scenario_steps.items()):
        if step < steps:
            plt.axvline(step, color=colors[i % len(colors)], linestyle='--', alpha=0.7)
    plt.title("Unused Inventory Over Time", fontsize=14, fontweight='bold')
    plt.xlabel("Time Step")
    plt.ylabel("Units")
    plt.grid(True, alpha=0.3)

    # Plot 5: Production Failures
    plt.subplot(2, 3, 5)
    plt.bar(range(steps), failure_values, color='red', alpha=0.7)
    for i, (scenario_type, step) in enumerate(scenario_steps.items()):
        if step < steps:
            plt.axvline(step, color=colors[i % len(colors)], linestyle='--', alpha=0.7)
    plt.title("Production Failures", fontsize=14, fontweight='bold')
    plt.xlabel("Time Step")
    plt.ylabel("Failures")
    plt.grid(True, alpha=0.3)

    # Plot 6: Sourcing Changes
    plt.subplot(2, 3, 6)
    sourcing_changes = model.metrics.get("sourcing_changes", [])
    if sourcing_changes:
        change_steps = [change['step'] for change in sourcing_changes]
        change_counts = {}
        for step in change_steps:
            change_counts[step] = change_counts.get(step, 0) + 1

        change_values = [change_counts.get(i, 0) for i in range(steps)]
        plt.bar(range(steps), change_values, color='purple', alpha=0.7)

        for i, (scenario_type, step) in enumerate(scenario_steps.items()):
            if step < steps:
                plt.axvline(step, color=colors[i % len(colors)], linestyle='--', alpha=0.7)

    plt.title("Sourcing Changes", fontsize=14, fontweight='bold')
    plt.xlabel("Time Step")
    plt.ylabel("Changes")
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


def fetch_database_data(engine, query_text=None):
    """
    Fetch data from database using the provided query

    Args:
        engine: SQLAlchemy engine connected to your database
        query_text: Custom SQL query text (optional)

    Returns:
        List of dictionaries containing the query results
    """

    if query_text is None:
        # Default query matching your example
        query_text = """
        SELECT
            p."productGroupId",
            p."description" AS "partDescription",
            p."categoryId",
            c."description" AS "categoryDescription",
            a."articleNo",
            a."articleProductName",
            a."price",
            a."countryOfOrigin",
            s."supplierId",
            s."supplierName"
        FROM
            "parts" AS p
        INNER JOIN "articlevehiclelink" AS avl
            ON p."productGroupId" = avl."productGroupId"
        INNER JOIN "articles" AS a
            ON avl."articleNo" = a."articleNo"
            AND avl."supplierId" = a."supplierId"
        INNER JOIN "suppliers" AS s
            ON a."supplierId" = s."supplierId"
        INNER JOIN "category" AS c
            ON p."categoryId" = c."categoryId"
        """

    query = text(query_text)

    with Session(engine) as session:
        result = session.exec(query)
        rows = result.fetchall()

        # Convert rows to list of dicts
        columns = result.keys()
        data = [dict(zip(columns, row)) for row in rows]

    return data


def run_enhanced_simulation_with_database_data(database_data, steps=30, scenarios=None, single_scenario=None):
    """Run enhanced simulation with database query results and scenario configurations

    Args:
        database_data: Database query results
        steps: Number of simulation steps
        scenarios: List of scenario dicts (for multiple scenarios)
        single_scenario: Single scenario dict (for testing one scenario at a time)
    """

    model = EnhancedSupplyChainModel(supplier_data=database_data, seed=42)

    # Analyze initial supplier setup
    model.analyze_supplier_diversity()

    # Track scenario steps for plotting
    scenario_steps = {}

    # Handle single scenario mode
    if single_scenario is not None:
        scenarios = [single_scenario]
        print(f"Running single scenario: {single_scenario['type']} at step {single_scenario['step']}")
    elif scenarios is None:
        # Default: no scenarios (baseline simulation)
        scenarios = []
        print("Running baseline simulation (no scenarios)")

    for t in range(steps):
        print(f"\n--- Time Step {t} ---")

        # Apply scenarios based on configuration
        for scenario in scenarios:
            if scenario['step'] == t:
                scenario_type = scenario['type']

                if scenario_type == 'supplier_disruption':
                    success = model.apply_supplier_disruption(
                        scenario['supplier'],
                        scenario['country'],
                        scenario['duration']
                    )
                    if success:
                        scenario_steps['supplier_disruption'] = t

                elif scenario_type == 'tariff_shock':
                    model.apply_tariff_shock(scenario['country'], scenario['tariff'])
                    scenario_steps['tariff_shock'] = t

                elif scenario_type == 'sanctions':
                    count = model.apply_sanctions(scenario['country'])
                    if count > 0:
                        scenario_steps['sanctions'] = t

                elif scenario_type == 'remove_sanctions':
                    model.remove_sanctions(scenario['country'])

                elif scenario_type == 'fx_shock':
                    model.apply_fx_shock(scenario['country'], scenario['rate'])
                    scenario_steps['fx_shock'] = t

        model.step()

        # Print status every 5 steps
        if t % 5 == 0:
            status = model.get_current_supply_chain_status()
            cost = status['component_cost']

            if cost != float('inf'):
                print(f"Current component cost: ${cost:.2f}")
            else:
                print("Cannot build components - supply chain disrupted")

            print(f"Components built: {status['components_built']}")

            if status['offline_suppliers']:
                print(f"Offline suppliers: {len(status['offline_suppliers'])}")
            if status['sanctioned_suppliers']:
                print(f"Sanctioned suppliers: {len(status['sanctioned_suppliers'])}")

    # Final analysis
    print(f"\n=== SIMULATION COMPLETE ===")
    final_status = model.get_current_supply_chain_status()
    print(f"Total components built: {final_status['components_built']}")

    final_cost = final_status['component_cost']
    if final_cost != float('inf'):
        print(f"Final component cost: ${final_cost:.2f}")
    else:
        print("Final status: Supply chain disrupted - cannot build components")

    print(f"Total production failures: {len(model.metrics['production_failures'])}")
    print(f"Total sourcing changes: {len(model.metrics.get('sourcing_changes', []))}")

    # Print scenario summary
    scenario_summary = model.get_scenario_summary()
    print(f"\nScenarios applied: {scenario_summary['total_scenarios']}")
    for scenario in scenario_summary['scenarios']:
        print(f"- Step {scenario['step']}: {scenario['type']} - {scenario}")

    # Create enhanced visualizations
    plot_enhanced_simulation_results(model, scenario_steps)

    return model


def run_enhanced_simulation_from_database(engine, steps=30, custom_query=None, scenarios=None, single_scenario=None):
    """
    Complete workflow: fetch data from database and run enhanced simulation

    Args:
        engine: SQLAlchemy engine connected to your database
        steps: Number of simulation steps to run
        custom_query: Optional custom SQL query text
        scenarios: List of scenario dictionaries (for multiple scenarios)
        single_scenario: Single scenario dict (for testing one scenario at a time)

    Returns:
        Completed simulation model
    """

    print("Fetching data from database...")
    database_data = fetch_database_data(engine, custom_query)

    print(f"Retrieved {len(database_data)} records from database")

    if not database_data:
        print("No data retrieved from database. Please check your query and database connection.")
        return None

    print("Starting enhanced simulation...")
    model = run_enhanced_simulation_with_database_data(database_data, steps, scenarios, single_scenario)

    return model


def run_enhanced_simulation_with_sample_data(steps=30, scenarios=None, single_scenario=None):
    """Run enhanced simulation with sample data for testing purposes

    Args:
        steps: Number of simulation steps
        scenarios: List of scenario dicts (for multiple scenarios)
        single_scenario: Single scenario dict (for testing one scenario at a time)
    """

    # Enhanced sample data with more suppliers for better scenario testing
    sample_database_data = [
        {
            'productGroupId': 100807, 'partDescription': 'Brake Caliper Mounting',
            'categoryId': 100027, 'categoryDescription': 'Brake Caliper',
            'articleNo': '741092', 'articleProductName': 'Brake Caliper',
            'price': 85.0, 'countryOfOrigin': 'Germany',
            'supplierId': 206, 'supplierName': 'A.B.S.'
        },
        {
            'productGroupId': 100807, 'partDescription': 'Brake Caliper Mounting',
            'categoryId': 100027, 'categoryDescription': 'Brake Caliper',
            'articleNo': 'CA3407R', 'articleProductName': 'Brake Caliper',
            'price': 95.0, 'countryOfOrigin': 'Japan',
            'supplierId': 381, 'supplierName': 'AISIN'
        },
        {
            'productGroupId': 100025, 'partDescription': 'Brake Master Cylinder',
            'categoryId': 100026, 'categoryDescription': 'Brake Master Cylinder',
            'articleNo': 'BMT-155', 'articleProductName': 'Brake Master Cylinder',
            'price': 65.0, 'countryOfOrigin': 'Japan',
            'supplierId': 150, 'supplierName': 'AISIN'
        },
        {
            'productGroupId': 100025, 'partDescription': 'Brake Master Cylinder',
            'categoryId': 100026, 'categoryDescription': 'Brake Master Cylinder',
            'articleNo': 'BMC-200', 'articleProductName': 'Brake Master Cylinder',
            'price': 70.0, 'countryOfOrigin': 'Germany',
            'supplierId': 206, 'supplierName': 'A.B.S.'
        },
        {
            'productGroupId': 100028, 'partDescription': 'Wheel Cylinders',
            'categoryId': 100028, 'categoryDescription': 'Wheel Cylinders',
            'articleNo': 'WCT-039', 'articleProductName': 'Wheel Brake Cylinder',
            'price': 25.0, 'countryOfOrigin': 'China',
            'supplierId': 150, 'supplierName': 'AISIN'
        },
        {
            'productGroupId': 100028, 'partDescription': 'Wheel Cylinders',
            'categoryId': 100028, 'categoryDescription': 'Wheel Cylinders',
            'articleNo': 'WC-100', 'articleProductName': 'Wheel Brake Cylinder',
            'price': 30.0, 'countryOfOrigin': 'Poland',
            'supplierId': 250, 'supplierName': 'TRW'
        },
        {
            'productGroupId': 100806, 'partDescription': 'Brake Caliper Parts',
            'categoryId': 100027, 'categoryDescription': 'Brake Caliper',
            'articleNo': 'SZ733', 'articleProductName': 'Piston, brake caliper',
            'price': 30.0, 'countryOfOrigin': 'Poland',
            'supplierId': 250, 'supplierName': 'TRW'
        },
        {
            'productGroupId': 100806, 'partDescription': 'Brake Caliper Parts',
            'categoryId': 100027, 'categoryDescription': 'Brake Caliper',
            'articleNo': 'BCP-500', 'articleProductName': 'Piston, brake caliper',
            'price': 35.0, 'countryOfOrigin': 'China',
            'supplierId': 300, 'supplierName': 'BREMBO'
        }
    ]

    print("Running enhanced simulation with sample data...")
    model = run_enhanced_simulation_with_database_data(sample_database_data, steps, scenarios, single_scenario)

    return model


def run_single_scenario_test(scenario_type, **kwargs):
    """Convenient function to test a single scenario type

    Args:
        scenario_type: 'supplier_disruption', 'tariff_shock', 'sanctions', 'fx_shock'
        **kwargs: Scenario-specific parameters

    Returns:
        Completed simulation model
    """

    # Default parameters for each scenario type
    default_params = {
        'supplier_disruption': {
            'step': 10,
            'supplier': 'AISIN',
            'country': 'Japan',
            'duration': 5
        },
        'tariff_shock': {
            'step': 10,
            'country': 'China',
            'tariff': 0.60
        },
        'sanctions': {
            'step': 10,
            'country': 'Germany'
        },
        'fx_shock': {
            'step': 10,
            'country': 'China',
            'rate': 1.4
        }
    }

    if scenario_type not in default_params:
        raise ValueError(f"Unknown scenario type: {scenario_type}")

    # Merge default params with user-provided kwargs
    scenario_params = default_params[scenario_type].copy()
    scenario_params.update(kwargs)
    scenario_params['type'] = scenario_type

    print(f"=== Testing Single Scenario: {scenario_type.upper().replace('_', ' ')} ===")
    print(f"Parameters: {scenario_params}")

    return run_enhanced_simulation_with_sample_data(
        steps=25,
        single_scenario=scenario_params
    )


def run_baseline_simulation(steps=25):
    """Run simulation with no scenarios (baseline for comparison)"""
    print("=== Running Baseline Simulation (No Scenarios) ===")
    return run_enhanced_simulation_with_sample_data(steps=steps)


def create_custom_scenarios():
    """Create custom scenario configurations for different testing purposes"""

    # Scenario Set 1: Supply Chain Resilience Test
    resilience_scenarios = [
        {'step': 3, 'type': 'supplier_disruption', 'supplier': 'AISIN', 'country': 'Japan', 'duration': 7},
        {'step': 8, 'type': 'tariff_shock', 'country': 'China', 'tariff': 0.75},
        {'step': 12, 'type': 'sanctions', 'country': 'Germany'},
        {'step': 18, 'type': 'remove_sanctions', 'country': 'Germany'},
        {'step': 15, 'type': 'fx_shock', 'country': 'China', 'rate': 1.4}
    ]

    # Scenario Set 2: Trade War Simulation
    trade_war_scenarios = [
        {'step': 5, 'type': 'tariff_shock', 'country': 'China', 'tariff': 0.30},
        {'step': 10, 'type': 'tariff_shock', 'country': 'China', 'tariff': 0.60},
        {'step': 15, 'type': 'sanctions', 'country': 'China'},
        {'step': 20, 'type': 'fx_shock', 'country': 'China', 'rate': 1.5}
    ]

    # Scenario Set 3: Regional Crisis
    regional_crisis_scenarios = [
        {'step': 4, 'type': 'supplier_disruption', 'supplier': 'A.B.S.', 'country': 'Germany', 'duration': 10},
        {'step': 6, 'type': 'supplier_disruption', 'supplier': 'TRW', 'country': 'Poland', 'duration': 8},
        {'step': 8, 'type': 'fx_shock', 'country': 'Germany', 'rate': 0.7},
        {'step': 10, 'type': 'fx_shock', 'country': 'Poland', 'rate': 0.8}
    ]

    return {
        'resilience': resilience_scenarios,
        'trade_war': trade_war_scenarios,
        'regional_crisis': regional_crisis_scenarios
    }


# Main execution examples
if __name__ == "__main__":
    print("=== Enhanced Supply Chain Simulation - Single Scenario Testing ===\n")

    # Option 1: Run baseline simulation (no scenarios)
    print("1. Baseline Simulation (No Disruptions)")
    baseline_model = run_baseline_simulation(steps=25)

    print("\n" + "=" * 60 + "\n")

    # Option 2: Test individual scenario types
    print("2. Testing Individual Scenarios")

    # Test supplier disruption
    print("\n--- Supplier Disruption Test ---")
    supplier_model = run_single_scenario_test(
        'supplier_disruption',
        step=8,  # When to apply the disruption
        supplier='AISIN',
        country='Japan',
        duration=7  # How long supplier is offline
    )

    print("\n--- Tariff Shock Test ---")
    tariff_model = run_single_scenario_test(
        'tariff_shock',
        step=10,
        country='China',
        tariff=0.75  # 75% tariff
    )

    print("\n--- Sanctions Test ---")
    sanctions_model = run_single_scenario_test(
        'sanctions',
        step=8,
        country='Germany'
    )

    print("\n--- FX Shock Test ---")
    fx_model = run_single_scenario_test(
        'fx_shock',
        step=12,
        country='China',
        rate=1.5  # 50% devaluation
    )

    # Option 3: Custom single scenario
    print("\n--- Custom Single Scenario ---")
    custom_scenario = {
        'step': 6,
        'type': 'supplier_disruption',
        'supplier': 'TRW',
        'country': 'Poland',
        'duration': 10
    }

    custom_model = run_enhanced_simulation_with_sample_data(
        steps=25,
        single_scenario=custom_scenario
    )

    # Option 4: Database single scenario (uncomment when ready)
    # from your_database_config import engine
    # print("\n--- Database Single Scenario ---")
    # db_scenario = {
    #     'step': 5,
    #     'type': 'tariff_shock',
    #     'country': 'China',
    #     'tariff': 0.50
    # }
    # db_model = run_enhanced_simulation_from_database(
    #     engine,
    #     steps=30,
    #     single_scenario=db_scenario
    # )

    print("\n=== All Single Scenario Tests Complete ===")
    print("Models available for further analysis:")
    print("- baseline_model: No disruptions")
    print("- supplier_model: Supplier disruption test")
    print("- tariff_model: Tariff shock test")
    print("- sanctions_model: Sanctions test")
    print("- fx_model: FX shock test")
    print("- custom_model: Custom scenario test")