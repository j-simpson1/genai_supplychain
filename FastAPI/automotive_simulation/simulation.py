import matplotlib.pyplot as plt
import numpy as np
import json
from collections import defaultdict
import os
from datetime import datetime


class TariffSimulation:
    """Enhanced tariff simulation with bottom quartile supplier selection"""

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
        # Get bottom quartile suppliers for baseline scenario
        self.bottom_quartile_suppliers = self._get_bottom_quartile_suppliers()
        # Set current suppliers to bottom quartile average
        self.current_suppliers = self._calculate_quartile_average_suppliers()

    def _group_suppliers(self):
        """Group suppliers by product ID"""
        groups = defaultdict(list)
        for supplier in self.suppliers_data:
            groups[supplier['productId']].append(supplier)
        return groups

    def _get_bottom_quartile_suppliers(self, tariffs=None):
        """Get bottom quartile suppliers for each product based on article number and tariff-adjusted prices"""
        if tariffs is None:
            tariffs = self.current_tariff_rates

        quartile_suppliers = {}

        for product_id in self.part_requirements:
            if product_id in self.suppliers_by_product:
                # Calculate tariff-adjusted prices for all suppliers of this product
                suppliers_with_data = []
                for supplier in self.suppliers_by_product[product_id]:
                    tariff_rate = tariffs.get(supplier['countryOfOrigin'], 0)
                    adjusted_price = supplier['price'] * (1 + tariff_rate)
                    suppliers_with_data.append({
                        'supplier': supplier,
                        'adjusted_price': adjusted_price,
                        'article_no': supplier.get('articleNo', ''),
                    })

                # Sort by article number first, then by adjusted price
                # This ensures consistent ordering when article numbers are the same
                suppliers_with_data.sort(key=lambda x: (x['article_no'], x['adjusted_price']))

                # Get bottom quartile (25% of suppliers)
                quartile_size = max(1, len(suppliers_with_data) // 4)
                bottom_quartile = suppliers_with_data[:quartile_size]

                quartile_suppliers[product_id] = [item['supplier'] for item in bottom_quartile]

        return quartile_suppliers

    def _calculate_quartile_average_suppliers(self, tariffs=None):
        """Calculate average price from bottom quartile suppliers for each product"""
        if tariffs is None:
            tariffs = self.current_tariff_rates

        average_suppliers = {}

        for product_id in self.part_requirements:
            if product_id in self.bottom_quartile_suppliers:
                quartile_suppliers = self.bottom_quartile_suppliers[product_id]

                # Calculate average price and select representative supplier
                total_adjusted_price = 0
                supplier_count = len(quartile_suppliers)

                for supplier in quartile_suppliers:
                    tariff_rate = tariffs.get(supplier['countryOfOrigin'], 0)
                    adjusted_price = supplier['price'] * (1 + tariff_rate)
                    total_adjusted_price += adjusted_price

                average_price = total_adjusted_price / supplier_count

                # Create a virtual supplier representing the quartile average
                # Use the first supplier as template but with average price
                template_supplier = quartile_suppliers[0].copy()

                # Calculate what the base price should be to achieve the average adjusted price
                # We'll use the most common country or the template's country for tariff calculation
                countries = [s['countryOfOrigin'] for s in quartile_suppliers]
                most_common_country = max(set(countries), key=countries.count)
                tariff_rate = tariffs.get(most_common_country, 0)

                # Back-calculate base price: average_price = base_price * (1 + tariff_rate)
                base_price = average_price / (1 + tariff_rate)

                template_supplier.update({
                    'price': base_price,
                    'countryOfOrigin': most_common_country,
                    'supplierName': f"Bottom Quartile Average ({supplier_count} suppliers)",
                    'articleProductName': template_supplier.get('articleProductName', 'Unknown'),
                    'articleNo': f"AVG-{product_id}"
                })

                average_suppliers[product_id] = template_supplier

        return average_suppliers

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
        """Run tariff shock simulation with consistent bottom quartile suppliers"""
        self.cost_history = []
        # Start with current tariff rates
        current_tariffs = self.current_tariff_rates.copy()

        for step in range(steps):
            if step == shock_step:
                # Apply tariff shock to target country
                current_tariffs[target_country] = tariff_rate
                # Recalculate costs with new tariffs but keep same supplier selection
                # (bottom quartile was determined at initialization)

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
                    'total_cost': total_product_cost,
                    'quartile_suppliers_count': len(self.bottom_quartile_suppliers.get(product_id, []))
                }

                total_cost += total_product_cost

        return cost_breakdown, total_cost

    def get_quartile_analysis(self):
        """Get detailed analysis of bottom quartile selection"""
        analysis = {}

        for product_id in self.part_requirements:
            if product_id in self.bottom_quartile_suppliers:
                quartile_suppliers = self.bottom_quartile_suppliers[product_id]
                all_suppliers = self.suppliers_by_product[product_id]

                # Calculate statistics
                quartile_prices = []
                all_prices = []

                for supplier in quartile_suppliers:
                    tariff_rate = self.current_tariff_rates.get(supplier['countryOfOrigin'], 0)
                    adjusted_price = supplier['price'] * (1 + tariff_rate)
                    quartile_prices.append(adjusted_price)

                for supplier in all_suppliers:
                    tariff_rate = self.current_tariff_rates.get(supplier['countryOfOrigin'], 0)
                    adjusted_price = supplier['price'] * (1 + tariff_rate)
                    all_prices.append(adjusted_price)

                analysis[product_id] = {
                    'total_suppliers': len(all_suppliers),
                    'quartile_suppliers': len(quartile_suppliers),
                    'quartile_percentage': (len(quartile_suppliers) / len(all_suppliers)) * 100,
                    'quartile_price_range': {
                        'min': min(quartile_prices),
                        'max': max(quartile_prices),
                        'average': np.mean(quartile_prices)
                    },
                    'all_suppliers_price_range': {
                        'min': min(all_prices),
                        'max': max(all_prices),
                        'average': np.mean(all_prices)
                    },
                    'savings_vs_average': np.mean(all_prices) - np.mean(quartile_prices),
                    'quartile_suppliers_details': [
                        {
                            'supplier_name': s['supplierName'],
                            'article_no': s.get('articleNo', ''),
                            'country': s['countryOfOrigin'],
                            'base_price': s['price'],
                            'adjusted_price': s['price'] * (1 + self.current_tariff_rates.get(s['countryOfOrigin'], 0))
                        }
                        for s in sorted(quartile_suppliers, key=lambda x: (x.get('articleNo', ''), x['price']))
                    ]
                }

        return analysis


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
    ax.set_title(f'Cost Impact - {target_country} Tariff Shock\n(Bottom Quartile by Article No. + Price)',
                 fontweight='bold',
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
        filename = f"cost_progression_quartile_{target_country.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        saved_path = os.path.abspath(filepath)
        print(f"Cost progression chart saved as: {saved_path}")

    if show_plot:
        plt.show()
    else:
        plt.close()

    return saved_path


def create_quartile_cost_distribution_chart(simulation, tariff_rates, target_country, show_plot=False, save_plot=True,
                                            output_dir='./charts'):
    """Create the quartile cost distribution boxplot chart showing total system costs after tariff shocks"""

    # Calculate cost distributions for each tariff scenario
    cost_distributions = []

    for tariff_rate in tariff_rates:
        # Create temporary tariff rates with the shock applied
        temp_tariffs = simulation.current_tariff_rates.copy()
        temp_tariffs[target_country] = tariff_rate

        # Calculate total system costs for all possible combinations
        system_costs = []

        # Get all possible supplier combinations for the complete system
        # We'll generate multiple system cost scenarios based on different supplier selections
        # from the bottom quartile of each component

        # First, collect all quartile suppliers for each product
        product_suppliers = {}
        for product_id in simulation.part_requirements:
            if product_id in simulation.bottom_quartile_suppliers:
                quartile_suppliers = simulation.bottom_quartile_suppliers[product_id]
                quantity = simulation.part_requirements[product_id]

                product_suppliers[product_id] = []
                for supplier in quartile_suppliers:
                    country = supplier['countryOfOrigin']
                    # Use the shock tariff if it's the target country, otherwise use current tariff
                    if country == target_country:
                        tariff_rate_to_use = tariff_rate
                    else:
                        tariff_rate_to_use = simulation.current_tariff_rates.get(country, 0)

                    # Calculate total cost for this component (all units)
                    unit_price = supplier['price']
                    adjusted_unit_price = unit_price * (1 + tariff_rate_to_use)
                    total_component_cost = adjusted_unit_price * quantity

                    product_suppliers[product_id].append({
                        'supplier': supplier,
                        'component_cost': total_component_cost,
                        'product_id': product_id
                    })

        # Generate system cost scenarios
        # For computational efficiency, we'll sample combinations rather than generate all permutations
        import itertools
        import random

        # Get supplier options for each product
        supplier_options = []
        for product_id in sorted(product_suppliers.keys()):
            supplier_options.append(product_suppliers[product_id])

        # Generate sample combinations (limit to reasonable number for performance)
        max_combinations = 1000
        if supplier_options:
            # Calculate total possible combinations
            total_combinations = 1
            for options in supplier_options:
                total_combinations *= len(options)

            if total_combinations <= max_combinations:
                # Generate all combinations if small enough
                for combination in itertools.product(*supplier_options):
                    total_system_cost = sum(item['component_cost'] for item in combination)
                    system_costs.append(total_system_cost)
            else:
                # Sample random combinations if too many
                random.seed(42)  # For reproducibility
                for _ in range(max_combinations):
                    combination = [random.choice(options) for options in supplier_options]
                    total_system_cost = sum(item['component_cost'] for item in combination)
                    system_costs.append(total_system_cost)

        cost_distributions.append(system_costs)

    # Create the chart
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))

    box_colors = ['lightblue', 'lightgreen', 'lightcoral']
    box_plot = ax.boxplot(cost_distributions, tick_labels=[f'{r:.0%}' for r in tariff_rates],
                          patch_artist=True)

    for patch, color in zip(box_plot['boxes'], box_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_title(
        f'Complete System Cost Distribution - {target_country} Tariff Shock\n(Total Cost for Entire Brake System from Bottom Quartile Suppliers)',
        fontweight='bold', fontsize=18)
    ax.set_xlabel('Tariff Rate', fontsize=16)
    ax.set_ylabel('Total System Cost (USD)', fontsize=16)
    ax.grid(True, alpha=0.3)

    # Add summary statistics as text
    for i, (costs, rate) in enumerate(zip(cost_distributions, tariff_rates)):
        if costs:  # Check if costs list is not empty
            median_cost = np.median(costs)
            mean_cost = np.mean(costs)
            max_cost = max(costs)
            min_cost = min(costs)
            ax.text(i + 1, max_cost * 1.02,
                    f'Median: ${median_cost:.2f}\nMean: ${mean_cost:.2f}\nRange: ${min_cost:.2f}-${max_cost:.2f}',
                    ha='center', va='bottom', fontsize=9,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

    # Increase tick label sizes
    ax.tick_params(axis='both', which='major', labelsize=14)
    ax.tick_params(axis='both', which='minor', labelsize=12)

    plt.tight_layout()

    saved_path = None
    if save_plot:
        os.makedirs(output_dir, exist_ok=True)
        filename = f"complete_system_cost_distribution_{target_country.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        saved_path = os.path.abspath(filepath)
        print(f"Complete system cost distribution chart saved as: {saved_path}")

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
    """Analyze tariff impact using bottom quartile average pricing with updated cost distribution chart"""

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
    quartile_analysis = sim.get_quartile_analysis()

    # Test different shock scenarios
    results = []

    for rate in tariff_rates:
        result = sim.run_simulation(target_country=target_country, tariff_rate=rate)

        # Calculate affected suppliers for this scenario
        affected_suppliers = []

        # Use the same approach but with the specific tariff rate for the target country
        temp_tariffs = current_tariffs.copy()
        temp_tariffs[target_country] = rate

        for supplier in suppliers_data:
            country = supplier['countryOfOrigin']
            if country == target_country:
                tariff_rate_to_use = rate
            else:
                tariff_rate_to_use = current_tariffs.get(country, 0)

            adjusted_price = supplier['price'] * (1 + tariff_rate_to_use)

            if country == target_country:
                affected_suppliers.append({
                    'supplier_name': supplier['supplierName'],
                    'article_no': supplier['articleNo'],
                    'current_tariff': current_tariffs.get(target_country, 0),
                    'shock_tariff': rate,
                    'original_price': supplier['price'],
                    'adjusted_price': adjusted_price,
                    'price_increase': adjusted_price - supplier['price'] * (1 + current_tariffs.get(target_country, 0))
                })

        # Build result
        scenario = {
            'tariff_rate': rate,
            'cost_analysis': {
                'initial_cost': result['initial_cost'],
                'final_cost': result['final_cost'],
                'cost_increase': result['cost_increase'],
                'percentage_increase': (result['cost_increase'] / result['initial_cost']) * 100 if result[
                                                                                                       'initial_cost'] > 0 else 0
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

    # Add quartile-specific recommendations
    avg_quartile_size = np.mean([q['quartile_suppliers'] for q in quartile_analysis.values()])
    if avg_quartile_size < 2:
        recommendations.append({
            'type': 'limited_supplier_base',
            'message': f"Limited supplier diversity - average {avg_quartile_size:.1f} suppliers in bottom quartile",
            'severity': 'high'
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

        # Create NEW complete system cost distribution chart
        system_cost_chart_path = create_quartile_cost_distribution_chart(
            sim, tariff_rates, target_country, show_plots, save_plots, output_dir
        )
        if system_cost_chart_path:
            chart_paths['complete_system_cost_distribution'] = system_cost_chart_path

    # Return JSON response
    response = {
        'analysis_type': 'tariff_impact_analysis_quartile',
        'methodology': 'bottom_quartile_selection_by_article_and_price',
        'target_country': target_country,
        'timestamp': datetime.now().isoformat(),
        'current_tariff_rates': current_tariffs,
        'current_cost_analysis': {
            'total_cost': current_total_cost,
            'cost_breakdown': current_cost_breakdown
        },
        'quartile_analysis': quartile_analysis,
        'summary': {
            'tariff_rates_tested': tariff_rates,
            'total_suppliers': len(suppliers_data),
            'affected_suppliers': len(results[0]['affected_suppliers']),
            'cost_range': {
                'min_increase': min(r['cost_analysis']['percentage_increase'] for r in results),
                'max_increase': max(r['cost_analysis']['percentage_increase'] for r in results)
            },
            'quartile_summary': {
                'avg_quartile_size': avg_quartile_size,
                'total_products': len(quartile_analysis),
                'avg_savings_vs_market': np.mean([q['savings_vs_average'] for q in quartile_analysis.values()])
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
    print("Running tariff impact analysis with updated quartile cost distribution chart...")
    result = analyze_tariff_impact(
        target_country='Germany',
        tariff_rates=[0.10, 0.30, 0.60],
        show_plots=True,
        save_plots=True
    )

    print(json.dumps(result, indent=2, default=str))