import matplotlib.pyplot as plt
import numpy as np
import json
from collections import defaultdict
import os
from datetime import datetime


class TariffSimulation:
    """Enhanced tariff simulation with current tariff rates"""

    def __init__(self, suppliers_data, part_requirements):
        self.suppliers_data = suppliers_data
        self.part_requirements = part_requirements
        self.cost_history = []

        # Current tariff rates by country (as of 2025) - initialize first
        self.current_tariff_rates = {
            'Germany': 0.025,  # EU standard automotive tariffs
            'Netherlands': 0.025,  # EU standard automotive tariffs
            'Denmark': 0.025,  # EU standard automotive tariffs
            'Italy': 0.025,  # EU standard automotive tariffs
            'Japan': 0.12,  # US-Japan trade agreement rates
            'China': 0.27,  # Current US-China trade tensions
            'South Korea': 0.08,  # KORUS agreement
            'Mexico': 0.0,  # USMCA agreement
            'Canada': 0.0,  # USMCA agreement
            'India': 0.15,  # Recent trade negotiations
            'Brazil': 0.18,  # Mercosur rates
            'United Kingdom': 0.035,  # Post-Brexit rates
            'Taiwan': 0.095,  # Recent semiconductor-related adjustments
            'Thailand': 0.065,  # ASEAN trade rates
            'Turkey': 0.055,  # EU customs union adjustments
        }

        # Now initialize suppliers after tariff rates are set
        self.suppliers_by_product = self._group_suppliers()
        self.current_suppliers = self._get_cheapest_suppliers()

    def _group_suppliers(self):
        """Group suppliers by product ID"""
        groups = defaultdict(list)
        for supplier in self.suppliers_data:
            groups[supplier['productId']].append(supplier)
        return groups

    def _get_cheapest_suppliers(self, tariffs=None):
        """Find cheapest supplier for each required product"""
        if tariffs is None:
            tariffs = self.current_tariff_rates

        suppliers = {}
        for product_id in self.part_requirements:
            if product_id in self.suppliers_by_product:
                best_supplier = min(
                    self.suppliers_by_product[product_id],
                    key=lambda s: s['price'] * (1 + tariffs.get(s['countryOfOrigin'], 0))
                )
                suppliers[product_id] = best_supplier
        return suppliers

    def get_total_cost(self, tariffs=None):
        """Calculate total cost with current suppliers"""
        if tariffs is None:
            tariffs = self.current_tariff_rates

        total = 0
        for product_id, quantity in self.part_requirements.items():
            if product_id in self.current_suppliers:
                supplier = self.current_suppliers[product_id]
                tariff_rate = tariffs.get(supplier['countryOfOrigin'], 0)
                cost = supplier['price'] * (1 + tariff_rate) * quantity
                total += cost
        return total

    def run_simulation(self, steps=25, shock_step=10, target_country='Germany', tariff_rate=0.30):
        """Run tariff shock simulation"""
        self.cost_history = []
        # Start with current tariff rates
        current_tariffs = self.current_tariff_rates.copy()

        for step in range(steps):
            if step == shock_step:
                # Apply tariff shock to target country
                current_tariffs[target_country] = tariff_rate
                self.current_suppliers = self._get_cheapest_suppliers(current_tariffs)

            cost = self.get_total_cost(current_tariffs)
            self.cost_history.append(cost)

        return {
            'initial_cost': self.cost_history[0],
            'final_cost': self.cost_history[-1],
            'cost_increase': self.cost_history[-1] - self.cost_history[0]
        }

    def get_current_tariff_info(self):
        """Return current tariff rates for all countries"""
        return self.current_tariff_rates.copy()

    def analyze_current_costs(self):
        """Analyze costs with current tariff rates"""
        cost_breakdown = {}
        total_cost = 0

        for product_id, quantity in self.part_requirements.items():
            if product_id in self.current_suppliers:
                supplier = self.current_suppliers[product_id]
                country = supplier['countryOfOrigin']
                tariff_rate = self.current_tariff_rates.get(country, 0)

                base_cost = supplier['price'] * quantity
                tariff_cost = base_cost * tariff_rate
                total_product_cost = base_cost + tariff_cost

                cost_breakdown[product_id] = {
                    'product_name': supplier.get('articleProductName', 'Unknown'),
                    'supplier': supplier['supplierName'],
                    'country': country,
                    'quantity': quantity,
                    'unit_price': supplier['price'],
                    'tariff_rate': tariff_rate,
                    'base_cost': base_cost,
                    'tariff_cost': tariff_cost,
                    'total_cost': total_product_cost
                }

                total_cost += total_product_cost

        return cost_breakdown, total_cost


import pandas as pd

def load_data_from_csv(articles_csv_path, parts_csv_path):
    """
    Load supplier articles and part requirements from CSV.
    """
    # Articles (suppliers)
    articles_df = pd.read_csv(articles_csv_path)

    suppliers_data = articles_df.rename(columns={
        "productGroupId": "productId"
    }).to_dict(orient="records")

    # Parts requirements
    parts_df = pd.read_csv(parts_csv_path)
    part_requirements = dict(zip(parts_df["productGroupId"], parts_df["quantity"]))

    # Also capture taxable flag if needed
    taxable_info = dict(zip(parts_df["productGroupId"], parts_df["taxable"]))

    return suppliers_data, part_requirements, taxable_info


def create_cost_progression_chart(results, target_country, show_plot=False, save_plot=True, output_dir='./charts'):
    """Create the cost progression chart separately"""
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))

    colors = ['blue', 'green', 'red']
    for i, result in enumerate(results):
        ax.plot(result['cost_progression'], label=f"Shock to {result['tariff_rate']:.0%}",
                color=colors[i], linewidth=3, marker='o', markersize=6)

    ax.axvline(10, color='red', linestyle='--', alpha=0.7, label='Tariff Shock', linewidth=2)
    ax.set_title(f'Cost Impact - {target_country} Tariff Shock\n(Starting from current rates)', fontweight='bold',
                 fontsize=18)
    ax.set_xlabel('Time Step', fontsize=16)
    ax.set_ylabel('Total Cost (USD)', fontsize=16)
    ax.legend(fontsize=14)
    ax.grid(True, alpha=0.3)

    # Increase tick label sizes
    ax.tick_params(axis='both', which='major', labelsize=14)
    ax.tick_params(axis='both', which='minor', labelsize=12)

    plt.tight_layout()

    saved_path = None
    if save_plot:
        os.makedirs(output_dir, exist_ok=True)
        filename = f"cost_progression_{target_country.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        saved_path = os.path.abspath(filepath)
        print(f"Cost progression chart saved as: {saved_path}")

    if show_plot:
        plt.show()
    else:
        plt.close()

    return saved_path


def create_price_distribution_chart(price_distributions, tariff_rates, target_country, show_plot=False, save_plot=True,
                                    output_dir='./charts'):
    """Create the price distribution boxplot chart separately"""
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))

    box_colors = ['lightblue', 'lightgreen', 'lightcoral']
    box_plot = ax.boxplot(price_distributions, tick_labels=[f'{r:.0%}' for r in tariff_rates],
                          patch_artist=True)

    for patch, color in zip(box_plot['boxes'], box_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_title(
        f'Price Distribution - {target_country} Tariff Shock\n(Including current rates for other countries)',
        fontweight='bold', fontsize=18)
    ax.set_xlabel('Tariff Rate', fontsize=16)
    ax.set_ylabel('Article Price (USD)', fontsize=16)
    ax.grid(True, alpha=0.3)

    # Increase tick label sizes
    ax.tick_params(axis='both', which='major', labelsize=14)
    ax.tick_params(axis='both', which='minor', labelsize=12)

    plt.tight_layout()

    saved_path = None
    if save_plot:
        os.makedirs(output_dir, exist_ok=True)
        filename = f"price_distribution_{target_country.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        saved_path = os.path.abspath(filepath)
        print(f"Price distribution chart saved as: {saved_path}")

    if show_plot:
        plt.show()
    else:
        plt.close()

    return saved_path


def analyze_tariff_impact(
        target_country='Germany',
        tariff_rates=None,
        show_plots=False,
        save_plots=True,
        output_dir='./charts'
):
    """Analyze tariff impact and create charts separately"""

    if tariff_rates is None:
        tariff_rates = [0.10, 0.30, 0.60]

    articles_csv_path = "../core/Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv"
    parts_csv_path = "../core/Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv"

    suppliers_data, part_requirements, taxable_info = load_data_from_csv(
        articles_csv_path, parts_csv_path
    )
    sim = TariffSimulation(suppliers_data, part_requirements)

    # Get current tariff information
    current_tariffs = sim.get_current_tariff_info()
    current_cost_breakdown, current_total_cost = sim.analyze_current_costs()

    # Test different shock scenarios
    results = []
    price_distributions = []

    for rate in tariff_rates:
        result = sim.run_simulation(target_country=target_country, tariff_rate=rate)

        # Calculate affected suppliers and prices
        affected_suppliers = []
        all_prices = []

        for supplier in suppliers_data:
            if supplier['countryOfOrigin'] == target_country:
                adjusted_price = supplier['price'] * (1 + rate)
                affected_suppliers.append({
                    'supplier_name': supplier['supplierName'],
                    'article_no': supplier['articleNo'],
                    'current_tariff': current_tariffs.get(target_country, 0),
                    'shock_tariff': rate,
                    'original_price': supplier['price'],
                    'adjusted_price': adjusted_price,
                    'price_increase': adjusted_price - supplier['price']
                })
                all_prices.append(adjusted_price)
            else:
                # Use current tariff rates for other countries
                current_rate = current_tariffs.get(supplier['countryOfOrigin'], 0)
                adjusted_price = supplier['price'] * (1 + current_rate)
                all_prices.append(adjusted_price)

        price_distributions.append(all_prices)

        # Build result
        scenario = {
            'tariff_rate': rate,
            'cost_analysis': {
                'initial_cost': result['initial_cost'],
                'final_cost': result['final_cost'],
                'cost_increase': result['cost_increase'],
                'percentage_increase': (result['cost_increase'] / result['initial_cost']) * 100
            },
            'price_statistics': {
                'min_price': min(all_prices),
                'max_price': max(all_prices),
                'mean_price': np.mean(all_prices),
                'median_price': np.median(all_prices)
            },
            'affected_suppliers': affected_suppliers,
            'cost_progression': sim.cost_history
        }

        results.append(scenario)

    # Generate recommendations
    recommendations = []
    worst_case = max(results, key=lambda x: x['cost_analysis']['percentage_increase'])

    if worst_case['cost_analysis']['percentage_increase'] > 15:
        recommendations.append({
            'type': 'high_impact_warning',
            'message': f"{worst_case['tariff_rate']:.0%} tariff causes {worst_case['cost_analysis']['percentage_increase']:.1f}% cost increase",
            'severity': 'high'
        })

    if len(results[0]['affected_suppliers']) > 3:
        recommendations.append({
            'type': 'diversification',
            'message': f"Consider diversifying suppliers - {len(results[0]['affected_suppliers'])} suppliers affected in {target_country}",
            'severity': 'medium'
        })

    # Add recommendation about current tariff exposure
    high_tariff_countries = [country for country, rate in current_tariffs.items() if rate > 0.10]
    if high_tariff_countries:
        recommendations.append({
            'type': 'current_exposure',
            'message': f"Currently exposed to high tariffs in: {', '.join(high_tariff_countries)}",
            'severity': 'medium'
        })

    # Create charts separately
    chart_paths = {}

    if show_plots or save_plots:
        # Create cost progression chart
        cost_chart_path = create_cost_progression_chart(
            results, target_country, show_plots, save_plots, output_dir
        )
        if cost_chart_path:
            chart_paths['cost_progression'] = cost_chart_path

        # Create price distribution chart
        price_chart_path = create_price_distribution_chart(
            price_distributions, tariff_rates, target_country, show_plots, save_plots, output_dir
        )
        if price_chart_path:
            chart_paths['price_distribution'] = price_chart_path

    # Return JSON response
    response = {
        'analysis_type': 'tariff_impact_analysis',
        'target_country': target_country,
        'timestamp': datetime.now().isoformat(),
        'current_tariff_rates': current_tariffs,
        'current_cost_analysis': {
            'total_cost': current_total_cost,
            'cost_breakdown': current_cost_breakdown
        },
        'summary': {
            'tariff_rates_tested': tariff_rates,
            'total_suppliers': len(suppliers_data),
            'affected_suppliers': len(results[0]['affected_suppliers']),
            'cost_range': {
                'min_increase': min(r['cost_analysis']['percentage_increase'] for r in results),
                'max_increase': max(r['cost_analysis']['percentage_increase'] for r in results)
            }
        },
        'scenarios': results,
        'recommendations': recommendations,
        'output_files': {
            'charts_saved': bool(chart_paths),
            'chart_paths': chart_paths,
            'output_directory': output_dir if chart_paths else None
        }
    }

    return response


if __name__ == "__main__":
    print("Running tariff impact analysis with CSV input...")
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    articles_csv_path = os.path.join(BASE_DIR, "../core/Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
    parts_csv_path = os.path.join(BASE_DIR, "../core/Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")

    suppliers_data, part_requirements, taxable_info = load_data_from_csv(
        articles_csv_path, parts_csv_path
    )
    print("Supplier Data: ", suppliers_data)
    print("Part Requirements", part_requirements)
    print("Taxable Info: ", taxable_info)
    sim = TariffSimulation(suppliers_data, part_requirements)

    # Print current tariff rates
    print("\nCurrent Tariff Rates:")
    current_rates = sim.get_current_tariff_info()
    for country, rate in sorted(current_rates.items()):
        print(f"{country}: {rate:.1%}")

    # JSON output
    print("\n" + "=" * 50)
    print("JSON OUTPUT:")
    print("=" * 50)
    result = analyze_tariff_impact(
        target_country='Germany',
        tariff_rates=[0.10, 0.30, 0.60],
        show_plots=True,
        save_plots=True
    )

    print(json.dumps(result, indent=2, default=str))