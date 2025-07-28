import matplotlib.pyplot as plt
import numpy as np
import json
from collections import defaultdict
import os
from datetime import datetime


class TariffSimulation:
    """Enhanced tariff simulation with bottom quartile supplier selection and VAT"""

    def __init__(self, suppliers_data, part_requirements, taxable_info, vat_rate=0.20):
        self.suppliers_data = suppliers_data
        self.part_requirements = part_requirements
        self.taxable_info = taxable_info
        self.vat_rate = vat_rate  # Default UK VAT rate of 20%
        self.cost_history = []

        # Current tariff rates by country (updated with provided rates)
        self.current_tariff_rates = {
            'Canada': 0.03394,
            'China': 0.06,
            'Croatia': 0.03824,
            'Cyprus': 0.03824,
            'Czech Republic': 0.03824,
            'Denmark': 0.03824,
            'Finland': 0.03824,
            'France': 0.03824,
            'Germany': 0.03824,
            'Hong Kong': 0.0,
            'Hungary': 0.03824,
            'Iceland': 0.0,
            'Italy': 0.03824,
            'Japan': 0.0,
            'Korea': 0.08,
            'Malta': 0.03824,
            'Netherlands': 0.03824,
            'New Zealand': 0.03545,
            'Poland': 0.03824,
            'Portugal': 0.03824,
            'Romania': 0.03824,
            'Singapore': 0.0,
            'Spain': 0.03824,
            'Sweden': 0.03824,
            'Switzerland': 0.0,
            'Turkey': 0.05925,
            'United Kingdom': 0.02208,
            'United States of America': 0.01307
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

    def _calculate_full_cost(self, base_price, country, product_id, tariffs=None):
        """Calculate full cost including tariffs and VAT"""
        if tariffs is None:
            tariffs = self.current_tariff_rates

        # Step 1: Apply tariff to base price
        tariff_rate = tariffs.get(country, 0)
        price_with_tariff = base_price * (1 + tariff_rate)

        # Step 2: Apply VAT if the part is taxable
        is_taxable = self.taxable_info.get(product_id, False)
        if is_taxable:
            final_price = price_with_tariff * (1 + self.vat_rate)
        else:
            final_price = price_with_tariff

        return {
            'base_price': base_price,
            'tariff_rate': tariff_rate,
            'tariff_amount': base_price * tariff_rate,
            'price_with_tariff': price_with_tariff,
            'is_taxable': is_taxable,
            'vat_rate': self.vat_rate if is_taxable else 0,
            'vat_amount': price_with_tariff * self.vat_rate if is_taxable else 0,
            'final_price': final_price
        }

    def _get_bottom_quartile_suppliers(self, tariffs=None):
        """Get bottom quartile suppliers for each product based on article number and full cost (tariff + VAT)"""
        if tariffs is None:
            tariffs = self.current_tariff_rates

        quartile_suppliers = {}

        for product_id in self.part_requirements:
            if product_id in self.suppliers_by_product:
                # Calculate full cost for all suppliers of this product
                suppliers_with_data = []
                for supplier in self.suppliers_by_product[product_id]:
                    cost_info = self._calculate_full_cost(
                        supplier['price'],
                        supplier['countryOfOrigin'],
                        product_id,
                        tariffs
                    )

                    suppliers_with_data.append({
                        'supplier': supplier,
                        'final_price': cost_info['final_price'],
                        'article_no': supplier.get('articleNo', ''),
                        'cost_breakdown': cost_info
                    })

                # Sort by article number first, then by final price
                suppliers_with_data.sort(key=lambda x: (x['article_no'], x['final_price']))

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

                # Calculate average final price and select representative supplier
                total_final_price = 0
                supplier_count = len(quartile_suppliers)

                for supplier in quartile_suppliers:
                    cost_info = self._calculate_full_cost(
                        supplier['price'],
                        supplier['countryOfOrigin'],
                        product_id,
                        tariffs
                    )
                    total_final_price += cost_info['final_price']

                average_final_price = total_final_price / supplier_count

                # Create a virtual supplier representing the quartile average
                template_supplier = quartile_suppliers[0].copy()

                # Calculate what the base price should be to achieve the average final price
                countries = [s['countryOfOrigin'] for s in quartile_suppliers]
                most_common_country = max(set(countries), key=countries.count)
                tariff_rate = tariffs.get(most_common_country, 0)
                is_taxable = self.taxable_info.get(product_id, False)

                # Back-calculate base price from final price
                # final_price = base_price * (1 + tariff_rate) * (1 + vat_rate if taxable else 1)
                if is_taxable:
                    base_price = average_final_price / ((1 + tariff_rate) * (1 + self.vat_rate))
                else:
                    base_price = average_final_price / (1 + tariff_rate)

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
        """Calculate total cost with current suppliers including VAT"""
        if tariffs is None:
            tariffs = self.current_tariff_rates

        total = 0
        for product_id, quantity in self.part_requirements.items():
            if product_id in self.current_suppliers:
                supplier = self.current_suppliers[product_id]
                cost_info = self._calculate_full_cost(
                    supplier['price'],
                    supplier['countryOfOrigin'],
                    product_id,
                    tariffs
                )
                cost = cost_info['final_price'] * quantity
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
        """Analyze costs with current tariff rates including VAT breakdown"""
        cost_breakdown = {}
        total_cost = 0

        for product_id, quantity in self.part_requirements.items():
            if product_id in self.current_suppliers:
                supplier = self.current_suppliers[product_id]
                country = supplier['countryOfOrigin']

                cost_info = self._calculate_full_cost(
                    supplier['price'],
                    country,
                    product_id
                )

                unit_cost_breakdown = cost_info
                total_base_cost = cost_info['base_price'] * quantity
                total_tariff_cost = cost_info['tariff_amount'] * quantity
                total_vat_cost = cost_info['vat_amount'] * quantity
                total_product_cost = cost_info['final_price'] * quantity

                cost_breakdown[product_id] = {
                    'product_name': supplier.get('articleProductName', 'Unknown'),
                    'supplier': supplier['supplierName'],
                    'country': country,
                    'quantity': quantity,
                    'unit_base_price': cost_info['base_price'],
                    'tariff_rate': cost_info['tariff_rate'],
                    'is_taxable': cost_info['is_taxable'],
                    'vat_rate': cost_info['vat_rate'],
                    'unit_final_price': cost_info['final_price'],
                    'total_base_cost': total_base_cost,
                    'total_tariff_cost': total_tariff_cost,
                    'total_vat_cost': total_vat_cost,
                    'total_cost': total_product_cost,
                    'quartile_suppliers_count': len(self.bottom_quartile_suppliers.get(product_id, []))
                }
                total_cost += total_product_cost

        return cost_breakdown, total_cost

    def get_quartile_analysis(self):
        """Get detailed analysis of bottom quartile selection including VAT"""
        analysis = {}

        for product_id in self.part_requirements:
            if product_id in self.bottom_quartile_suppliers:
                quartile_suppliers = self.bottom_quartile_suppliers[product_id]
                all_suppliers = self.suppliers_by_product[product_id]

                # Calculate statistics
                quartile_prices = []
                all_prices = []

                for supplier in quartile_suppliers:
                    cost_info = self._calculate_full_cost(
                        supplier['price'],
                        supplier['countryOfOrigin'],
                        product_id
                    )
                    quartile_prices.append(cost_info['final_price'])

                for supplier in all_suppliers:
                    cost_info = self._calculate_full_cost(
                        supplier['price'],
                        supplier['countryOfOrigin'],
                        product_id
                    )
                    all_prices.append(cost_info['final_price'])

                analysis[product_id] = {
                    'total_suppliers': len(all_suppliers),
                    'quartile_suppliers': len(quartile_suppliers),
                    'quartile_percentage': (len(quartile_suppliers) / len(all_suppliers)) * 100,
                    'is_taxable': self.taxable_info.get(product_id, False),
                    'vat_rate': self.vat_rate if self.taxable_info.get(product_id, False) else 0,
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
                            'cost_breakdown': self._calculate_full_cost(
                                s['price'],
                                s['countryOfOrigin'],
                                product_id
                            )
                        }
                        for s in sorted(quartile_suppliers, key=lambda x: (x.get('articleNo', ''), x['price']))
                    ]
                }

        return analysis

    def get_vat_summary(self):
        """Get summary of VAT impact across all products"""
        taxable_products = [pid for pid, is_taxable in self.taxable_info.items() if is_taxable]
        non_taxable_products = [pid for pid, is_taxable in self.taxable_info.items() if not is_taxable]

        cost_breakdown, total_cost = self.analyze_current_costs()

        total_vat = sum(item['total_vat_cost'] for item in cost_breakdown.values())
        total_base_cost = sum(item['total_base_cost'] for item in cost_breakdown.values())
        total_tariff_cost = sum(item['total_tariff_cost'] for item in cost_breakdown.values())

        return {
            'vat_rate': self.vat_rate,
            'taxable_products_count': len(taxable_products),
            'non_taxable_products_count': len(non_taxable_products),
            'total_products': len(self.part_requirements),
            'cost_summary': {
                'total_base_cost': total_base_cost,
                'total_tariff_cost': total_tariff_cost,
                'total_vat_cost': total_vat,
                'total_final_cost': total_cost
            },
            'vat_percentage_of_total': (total_vat / total_cost) * 100 if total_cost > 0 else 0,
            'taxable_products': taxable_products,
            'non_taxable_products': non_taxable_products
        }


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

    # Taxable flag
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
    ax.set_title(f'Total Cost Impact - {target_country} Tariff Shock\n(Bottom Quartile with VAT)',
                 fontweight='bold',
                 fontsize=18)
    ax.set_xlabel('Time Step', fontsize=16)
    ax.set_ylabel('Total Cost (GBP)', fontsize=16)
    ax.legend(fontsize=14)
    ax.grid(True, alpha=0.3)

    # Increase tick label sizes
    ax.tick_params(axis='both', which='major', labelsize=14)
    ax.tick_params(axis='both', which='minor', labelsize=12)

    plt.tight_layout()

    saved_path = None
    if save_plot:
        os.makedirs(output_dir, exist_ok=True)
        filename = f"cost_progression_with_vat_{target_country.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
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
    """Create the quartile cost distribution boxplot chart showing total system costs after tariff shocks with VAT"""

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

                    # Create temporary tariff dict for this calculation
                    temp_tariff_dict = simulation.current_tariff_rates.copy()
                    temp_tariff_dict[country] = tariff_rate_to_use

                    # Calculate total cost for this component including VAT
                    cost_info = simulation._calculate_full_cost(
                        supplier['price'],
                        country,
                        product_id,
                        temp_tariff_dict
                    )
                    total_component_cost = cost_info['final_price'] * quantity

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
        f'Complete System Cost Distribution - {target_country} Tariff Shock\n(Bottom Quartile with VAT)',
        fontweight='bold', fontsize=18)
    ax.set_xlabel('Tariff Rate', fontsize=16)
    ax.set_ylabel('Total Cost (GBP)', fontsize=16)
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
        filename = f"complete_system_cost_distribution_with_vat_{target_country.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        saved_path = os.path.abspath(filepath)
        print(f"Complete system cost distribution chart saved as: {saved_path}")

    if show_plot:
        plt.show()
    else:
        plt.close()

    return saved_path


def analyze_tariff_impact_with_vat(
        target_country='Germany',
        tariff_rates=None,
        vat_rate=0.20,  # UK VAT rate
        show_plots=False,
        save_plots=True,
        output_dir='./charts'
):
    """Analyze tariff impact using bottom quartile average pricing with VAT included"""

    if tariff_rates is None:
        tariff_rates = [0.10, 0.30, 0.60]

    articles_csv_path = "../core/Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv"
    parts_csv_path = "../core/Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv"

    suppliers_data, part_requirements, taxable_info = load_data_from_csv(
        articles_csv_path, parts_csv_path
    )
    sim = TariffSimulation(suppliers_data, part_requirements, taxable_info, vat_rate)

    # Get current tariff information
    current_tariffs = sim.get_current_tariff_info()
    current_cost_breakdown, current_total_cost = sim.analyze_current_costs()
    quartile_analysis = sim.get_quartile_analysis()
    vat_summary = sim.get_vat_summary()

    # Test different shock scenarios
    results = []

    for rate in tariff_rates:
        result = sim.run_simulation(target_country=target_country, tariff_rate=rate)

        # Calculate affected suppliers for this scenario
        affected_suppliers = []

        temp_tariffs = current_tariffs.copy()
        temp_tariffs[target_country] = rate

        for supplier in suppliers_data:
            country = supplier['countryOfOrigin']
            if country == target_country:
                product_id = supplier['productId']

                # Calculate costs with current and shock tariffs
                current_cost = sim._calculate_full_cost(supplier['price'], country, product_id, current_tariffs)
                shock_cost = sim._calculate_full_cost(supplier['price'], country, product_id, temp_tariffs)

                affected_suppliers.append({
                    'supplier_name': supplier['supplierName'],
                    'article_no': supplier['articleNo'],
                    'product_id': product_id,
                    'is_taxable': taxable_info.get(product_id, False),
                    'current_tariff': current_tariffs.get(target_country, 0),
                    'shock_tariff': rate,
                    'original_price': supplier['price'],
                    'current_final_price': current_cost['final_price'],
                    'shock_final_price': shock_cost['final_price'],
                    'price_increase': shock_cost['final_price'] - current_cost['final_price'],
                    'current_cost_breakdown': current_cost,
                    'shock_cost_breakdown': shock_cost
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

    # Generate recommendations including VAT considerations
    recommendations = []
    worst_case = max(results, key=lambda x: x['cost_analysis']['percentage_increase'])

    if worst_case['cost_analysis']['percentage_increase'] > 15:
        recommendations.append({
            'type': 'high_impact_warning',
            'message': f"{worst_case['tariff_rate']:.0%} tariff causes {worst_case['cost_analysis']['percentage_increase']:.1f}% cost increase (including VAT)",
            'severity': 'high'
        })

    # VAT-specific recommendations
    if vat_summary['vat_percentage_of_total'] > 15:
        recommendations.append({
            'type': 'vat_impact',
            'message': f"VAT accounts for {vat_summary['vat_percentage_of_total']:.1f}% of total costs - consider VAT optimization strategies",
            'severity': 'medium'
        })

    taxable_count = len([s for s in results[0]['affected_suppliers'] if s['is_taxable']])
    if taxable_count > 0:
        recommendations.append({
            'type': 'taxable_supplier_exposure',
            'message': f"{taxable_count} affected suppliers have taxable parts - tariff increases will compound with VAT",
            'severity': 'high'
        })

    # Create charts
    chart_paths = {}

    if show_plots or save_plots:
        # Create cost progression chart
        cost_chart_path = create_cost_progression_chart(
            results, target_country, show_plots, save_plots, output_dir
        )
        if cost_chart_path:
            chart_paths['cost_progression'] = cost_chart_path

        # Create box and whisker plot (quartile cost distribution)
        distribution_chart_path = create_quartile_cost_distribution_chart(
            sim, tariff_rates, target_country, show_plots, save_plots, output_dir
        )
        if distribution_chart_path:
            chart_paths['cost_distribution'] = distribution_chart_path

    # Return JSON response
    response = {
        'analysis_type': 'tariff_impact_analysis_with_vat',
        'methodology': 'bottom_quartile_selection_with_vat_calculation',
        'target_country': target_country,
        'vat_rate': vat_rate,
        'timestamp': datetime.now().isoformat(),
        'current_tariff_rates': current_tariffs,
        'vat_summary': vat_summary,
        'current_cost_analysis': {
            'total_cost': current_total_cost,
            'cost_breakdown': current_cost_breakdown
        },
        'quartile_analysis': quartile_analysis,
        'summary': {
            'tariff_rates_tested': tariff_rates,
            'total_suppliers': len(suppliers_data),
            'affected_suppliers': len(results[0]['affected_suppliers']),
            'taxable_affected_suppliers': len([s for s in results[0]['affected_suppliers'] if s['is_taxable']]),
            'cost_range': {
                'min_increase': min(r['cost_analysis']['percentage_increase'] for r in results),
                'max_increase': max(r['cost_analysis']['percentage_increase'] for r in results)
            },
            'quartile_summary': {
                'avg_quartile_size': np.mean([q['quartile_suppliers'] for q in quartile_analysis.values()]),
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
    print("Running tariff impact analysis with VAT inclusion...")
    result = analyze_tariff_impact_with_vat(
        target_country='Germany',
        tariff_rates=[0.10, 0.30, 0.60],
        vat_rate=0.20,  # 20% VAT
        show_plots=True,
        save_plots=True
    )

    print(json.dumps(result, indent=2, default=str))