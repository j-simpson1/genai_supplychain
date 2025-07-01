from FastAPI.automotive_abm.model import SupplyChainModel
import matplotlib.pyplot as plt
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import text


def plot_simulation_results(model, tariff_shock_step=8):
    """Create visualization plots for simulation results"""
    steps = len(model.metrics["cost_history"])

    # Calculate production failures by step
    failure_counts = {}
    for step, _ in model.metrics["production_failures"]:
        failure_counts[step] = failure_counts.get(step, 0) + 1

    failure_values = [failure_counts.get(i, 0) for i in range(steps)]

    # Create 2x2 plot grid
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


def run_simulation_with_database_data(database_data, steps=24):
    """Run simulation with database query results and create plots"""

    model = SupplyChainModel(supplier_data=database_data, seed=42)

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
            inventory_sample = dict(list(model.parts_inventory.items())[:3])
            print(f"Current inventory levels: {inventory_sample}...")

    # Final analysis
    print(f"\n=== SIMULATION COMPLETE ===")
    print(f"Total components built: {model.manufacturer.components_built}")
    print(f"Final component cost: ${model.manufacturer.get_component_cost():.2f}")
    print(f"Total production failures: {len(model.metrics['production_failures'])}")

    # Create visualizations
    plot_simulation_results(model, tariff_shock_step)

    return model


def run_simulation_from_database(engine, steps=24, custom_query=None):
    """
    Complete workflow: fetch data from database and run simulation

    Args:
        engine: SQLAlchemy engine connected to your database
        steps: Number of simulation steps to run
        custom_query: Optional custom SQL query text

    Returns:
        Completed simulation model
    """

    print("Fetching data from database...")
    database_data = fetch_database_data(engine, custom_query)

    print(f"Retrieved {len(database_data)} records from database")

    if not database_data:
        print("No data retrieved from database. Please check your query and database connection.")
        return None

    print("Starting simulation...")
    model = run_simulation_with_database_data(database_data, steps)

    return model


# Example usage with sample data (for testing without database)
def run_simulation_with_sample_data(steps=24):
    """Run simulation with sample data for testing purposes"""

    # Sample data mimicking your database structure
    sample_database_data = [
        {
            'productGroupId': 100807,
            'partDescription': 'Brake Caliper Mounting',
            'categoryId': 100027,
            'categoryDescription': 'Brake Caliper',
            'articleNo': '741092',
            'articleProductName': 'Brake Caliper',
            'price': 85.0,
            'countryOfOrigin': 'Germany',
            'supplierId': 206,
            'supplierName': 'A.B.S.'
        },
        {
            'productGroupId': 100807,
            'partDescription': 'Brake Caliper Mounting',
            'categoryId': 100027,
            'categoryDescription': 'Brake Caliper',
            'articleNo': 'CA3407R',
            'articleProductName': 'Brake Caliper',
            'price': None,  # Missing price - will be estimated
            'countryOfOrigin': None,  # Missing country - will use 'Unknown'
            'supplierId': 381,
            'supplierName': 'Brake ENGINEERING'
        },
        {
            'productGroupId': 100025,
            'partDescription': 'Brake Master Cylinder',
            'categoryId': 100026,
            'categoryDescription': 'Brake Master Cylinder',
            'articleNo': 'BMT-155',
            'articleProductName': 'Brake Master Cylinder',
            'price': 65.0,
            'countryOfOrigin': 'Japan',
            'supplierId': 150,
            'supplierName': 'AISIN'
        },
        {
            'productGroupId': 100028,
            'partDescription': 'Wheel Cylinders',
            'categoryId': 100028,
            'categoryDescription': 'Wheel Cylinders',
            'articleNo': 'WCT-039',
            'articleProductName': 'Wheel Brake Cylinder',
            'price': 25.0,
            'countryOfOrigin': 'China',
            'supplierId': 150,
            'supplierName': 'AISIN'
        },
        {
            'productGroupId': 100806,
            'partDescription': 'Brake Caliper Parts',
            'categoryId': 100027,
            'categoryDescription': 'Brake Caliper',
            'articleNo': 'SZ733',
            'articleProductName': 'Piston, brake caliper',
            'price': 30.0,
            'countryOfOrigin': 'Poland',
            'supplierId': 250,
            'supplierName': 'TRW'
        }
    ]

    print("Running simulation with sample data...")
    model = run_simulation_with_database_data(sample_database_data, steps)

    return model


# Main execution
if __name__ == "__main__":
    # Option 1: Run with sample data (for testing)
    print("=== Running with Sample Data ===")
    model = run_simulation_with_sample_data(steps=24)

    # Option 2: Run with actual database (uncomment when ready)
    # from your_database_config import engine  # Import your database engine
    # print("=== Running with Database Data ===")
    # model = run_simulation_from_database(engine, steps=24)

    # Option 3: Use custom query (uncomment and modify as needed)
    # custom_query = """
    # SELECT
    #     your_custom_query_here
    # """
    # model = run_simulation_from_database(engine, steps=24, custom_query=custom_query)