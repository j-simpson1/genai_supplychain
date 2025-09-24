"""Tariff simulation module for automotive supply chain analysis."""

import itertools
import json
import os
import random
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import re


def normalize_country_name_for_filename(country_name: str) -> str:
    """Normalize country name for use in filenames by replacing spaces and special characters."""
    # Convert to lowercase, replace spaces with underscores, and remove special characters
    normalized = re.sub(r'[^\w\s-]', '', country_name.lower())
    normalized = re.sub(r'[\s-]+', '_', normalized)
    return normalized.strip('_')


class TariffSimulation:
    """Enhanced tariff simulation with Q1 threshold bottom quartile methodology and VAT.

    This class simulates the impact of tariff changes on automotive supply chain costs,
    using Q1 threshold methodology for supplier selection and including VAT calculations.
    """

    def __init__(self, suppliers_data: List[Dict], part_requirements: Dict[str, int],
                 taxable_info: Dict[str, bool], vat_rate: float = 0.20):
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
        # Calculate bottom quartile average prices using Q1 threshold
        self.current_suppliers = self._calculate_q1_threshold_suppliers()

    def _group_suppliers(self) -> Dict[str, List[Dict]]:
        """Group suppliers by product ID.

        Returns:
            Dictionary mapping product IDs to lists of suppliers.
        """
        groups = defaultdict(list)
        for supplier in self.suppliers_data:
            groups[supplier['productId']].append(supplier)
        return groups

    def _calculate_full_cost(self, base_price: float, country: str, product_id: str,
                            tariffs: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Calculate full cost including tariffs and VAT.

        Args:
            base_price: Base price before tariffs and VAT
            country: Country of origin for tariff calculation
            product_id: Product identifier for VAT lookup
            tariffs: Optional custom tariff rates, defaults to current rates

        Returns:
            Dictionary containing cost breakdown details.
        """
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

    def _calculate_q1_threshold_suppliers(self, tariffs: Optional[Dict[str, float]] = None) -> Dict[str, Dict]:
        """Calculate bottom quartile average using Q1 threshold methodology.

        This matches the reference function: finds Q1 (25th percentile) and
        averages all prices at or below that threshold.

        Args:
            tariffs: Optional custom tariff rates

        Returns:
            Dictionary mapping product IDs to average supplier information.
        """
        if tariffs is None:
            tariffs = self.current_tariff_rates

        average_suppliers = {}

        for product_id in self.part_requirements:
            if product_id in self.suppliers_by_product:
                suppliers = self.suppliers_by_product[product_id]

                # Calculate final prices for all suppliers
                supplier_prices = []
                for supplier in suppliers:
                    cost_info = self._calculate_full_cost(
                        supplier['price'],
                        supplier['countryOfOrigin'],
                        product_id,
                        tariffs
                    )
                    supplier_prices.append({
                        'supplier': supplier,
                        'final_price': cost_info['final_price'],
                        'cost_breakdown': cost_info
                    })

                # Sort by final price
                supplier_prices.sort(key=lambda x: x['final_price'])
                prices_array = np.array([sp['final_price'] for sp in supplier_prices])

                if len(prices_array) == 1:
                    # Single supplier case
                    avg_final_price = prices_array[0]
                    selected_suppliers = supplier_prices[:1]
                else:
                    # Calculate Q1 threshold (25th percentile)
                    q1_threshold = np.percentile(prices_array, 25)

                    # Get all suppliers at or below Q1 threshold
                    below_q1_suppliers = [sp for sp in supplier_prices if sp['final_price'] <= q1_threshold]

                    # Calculate average of prices at or below Q1
                    below_q1_prices = [sp['final_price'] for sp in below_q1_suppliers]
                    avg_final_price = np.mean(below_q1_prices)
                    selected_suppliers = below_q1_suppliers

                # Create a virtual supplier representing the Q1 average
                # Use the most common country from selected suppliers
                countries = [sp['supplier']['countryOfOrigin'] for sp in selected_suppliers]
                most_common_country = max(set(countries), key=countries.count)

                # Get tariff rate for the most common country
                tariff_rate = tariffs.get(most_common_country, 0)
                is_taxable = self.taxable_info.get(product_id, False)

                # Back-calculate base price from average final price
                if is_taxable:
                    base_price = avg_final_price / ((1 + tariff_rate) * (1 + self.vat_rate))
                else:
                    base_price = avg_final_price / (1 + tariff_rate)

                # Use first supplier as template
                template_supplier = suppliers[0].copy()
                template_supplier.update({
                    'price': base_price,
                    'countryOfOrigin': most_common_country,
                    'supplierName': f"Q1 Threshold Average ({len(selected_suppliers)} suppliers)",
                    'articleNo': f"Q1-AVG-{product_id}",
                    'q1_threshold': q1_threshold,
                    'suppliers_below_q1': len(selected_suppliers),
                    'total_suppliers': len(suppliers)
                })

                average_suppliers[product_id] = template_supplier

        return average_suppliers

    def get_total_cost(self, tariffs: Optional[Dict[str, float]] = None) -> float:
        """Calculate total cost with current suppliers including VAT.

        Args:
            tariffs: Optional custom tariff rates

        Returns:
            Total cost across all required parts.
        """
        if tariffs is None:
            tariffs = self.current_tariff_rates

        total = 0
        for product_id, quantity in self.part_requirements.items():
            if product_id in self.current_suppliers:
                supplier = self.current_suppliers[product_id]
                try:
                    cost_info = self._calculate_full_cost(
                        supplier['price'],
                        supplier['countryOfOrigin'],
                        product_id,
                        tariffs
                    )
                    cost = cost_info['final_price'] * quantity
                    total += cost
                except (KeyError, TypeError) as e:
                    print(f"Warning: Error calculating cost for product {product_id}: {e}")
                    continue
        return total

    def run_simulation(self, steps: int = 25, shock_step: int = 10,
                      target_country: str = 'Germany', tariff_rate: float = 0.30) -> Dict[str, float]:
        """Run tariff shock simulation with Q1 threshold methodology.

        Args:
            steps: Number of simulation steps
            shock_step: Step at which to apply tariff shock
            target_country: Country to apply tariff shock to
            tariff_rate: New tariff rate to apply

        Returns:
            Dictionary containing simulation results.
        """
        self.cost_history = []
        # Start with current tariff rates
        current_tariffs = self.current_tariff_rates.copy()

        # Keep the original Q1 suppliers selection (don't recalculate after shock)
        # This maintains consistency - we're testing the same supplier set under different tariff conditions
        original_suppliers = self.current_suppliers.copy()

        for step in range(steps):
            if step == shock_step:
                # Apply tariff shock to target country
                current_tariffs[target_country] = tariff_rate
                # NOTE: We do NOT recalculate suppliers here - we keep the same suppliers
                # to see how the tariff shock affects the existing supply chain

            cost = self.get_total_cost(current_tariffs)
            self.cost_history.append(cost)

        return {
            'initial_cost': self.cost_history[0],
            'final_cost': self.cost_history[-1],
            'cost_increase': self.cost_history[-1] - self.cost_history[0]
        }

    def get_current_tariff_info(self) -> Dict[str, float]:
        """Return current tariff rates for all countries.

        Returns:
            Copy of current tariff rates dictionary.
        """
        return self.current_tariff_rates.copy()

    def analyze_current_costs(self) -> Tuple[Dict[str, Dict], float]:
        """Analyze costs with current tariff rates including VAT breakdown.

        Returns:
            Tuple of (cost breakdown by product, total cost).
        """
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

                total_base_cost = cost_info['base_price'] * quantity
                total_tariff_cost = cost_info['tariff_amount'] * quantity
                total_vat_cost = cost_info['vat_amount'] * quantity
                total_product_cost = cost_info['final_price'] * quantity

                cost_breakdown[product_id] = {
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
                    'q1_threshold': supplier.get('q1_threshold', 'N/A'),
                    'suppliers_below_q1': supplier.get('suppliers_below_q1', 'N/A'),
                    'total_suppliers': supplier.get('total_suppliers', 'N/A')
                }
                total_cost += total_product_cost

        return cost_breakdown, total_cost

    def get_q1_analysis(self) -> Dict[str, Dict]:
        """Get detailed analysis of Q1 threshold selection including VAT.

        Returns:
            Dictionary containing Q1 analysis for each product.
        """
        analysis = {}

        for product_id in self.part_requirements:
            if product_id in self.suppliers_by_product:
                suppliers = self.suppliers_by_product[product_id]

                # Calculate all final prices
                all_prices = []
                for supplier in suppliers:
                    cost_info = self._calculate_full_cost(
                        supplier['price'],
                        supplier['countryOfOrigin'],
                        product_id
                    )
                    all_prices.append(cost_info['final_price'])

                all_prices_array = np.array(all_prices)

                if len(all_prices) == 1:
                    q1_threshold = all_prices[0]
                    below_q1_prices = all_prices
                else:
                    q1_threshold = np.percentile(all_prices_array, 25)
                    below_q1_prices = all_prices_array[all_prices_array <= q1_threshold]

                analysis[product_id] = {
                    'total_suppliers': len(suppliers),
                    'q1_price_stats': {
                        'min': float(np.min(below_q1_prices)),
                        'max': float(np.max(below_q1_prices)),
                        'average': float(np.mean(below_q1_prices))
                    },
                    'all_suppliers_price_stats': {
                        'min': float(np.min(all_prices_array)),
                        'max': float(np.max(all_prices_array)),
                        'average': float(np.mean(all_prices_array)),
                        'median': float(np.median(all_prices_array))
                    },
                    'savings_vs_average': float(np.mean(all_prices_array) - np.mean(below_q1_prices))
                }

        return analysis

    def get_vat_summary(self) -> Dict[str, Any]:
        """Get summary of VAT impact across all products.

        Returns:
            Dictionary containing VAT summary statistics.
        """
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
            'total_parts': len(self.part_requirements),
            'cost_summary': {
                'total_base_cost': total_base_cost,
                'total_tariff_cost': total_tariff_cost,
                'total_vat_cost': total_vat,
                'total_final_cost': total_cost
            },
            'vat_percentage_of_total': (total_vat / total_cost) * 100 if total_cost > 0 else 0,
        }

    def bottom_quartile_avg_verification(self, product_id: str) -> Optional[float]:
        """Verification function for Q1 implementation.

        Uses the exact same logic as the reference function to confirm
        our Q1 implementation is correct.

        Args:
            product_id: Product ID to verify

        Returns:
            Verified Q1 average price or None if product not found.
        """
        if product_id not in self.suppliers_by_product:
            return None

        suppliers = self.suppliers_by_product[product_id]

        # Get all final prices (same as our main calculation)
        prices = []
        for supplier in suppliers:
            cost_info = self._calculate_full_cost(
                supplier['price'],
                supplier['countryOfOrigin'],
                product_id
            )
            prices.append(cost_info['final_price'])

        # Convert to pandas Series and apply your exact logic
        if not prices:
            return None

        s = pd.Series(prices)
        s = pd.to_numeric(s, errors="coerce").dropna()

        if s.empty:
            return 0.0
        if len(s) == 1:
            return round(float(s.iloc[0]), 2)

        q1 = s.quantile(0.25)
        val = float(s[s <= q1].mean())
        return round(val, 2)


def load_data_from_csv(suppliers_csv_path, parts_csv_path):
    """
    Load supplier data and part requirements from the new CSV format.

    Suppliers CSV: productId,articleNo,price,countryOfOrigin,supplierId,supplierName
    Parts CSV: productId,partDescription,quantity,taxable
    """
    # Load suppliers data
    suppliers_df = pd.read_csv(suppliers_csv_path)

    # Convert to list of dictionaries (no column renaming needed now)
    suppliers_data = suppliers_df.to_dict(orient="records")

    # Load parts requirements
    parts_df = pd.read_csv(parts_csv_path)
    part_requirements = dict(zip(parts_df["productId"], parts_df["quantity"]))

    # Load taxable information
    taxable_info = dict(zip(parts_df["productId"], parts_df["taxable"]))

    return suppliers_data, part_requirements, taxable_info


def create_cost_progression_chart(results: List[Dict], target_country: str, show_plot: bool = False,
                                 save_plot: bool = True, output_dir: str = './charts') -> Optional[str]:
    """Create cost progression chart showing tariff impact over time.

    Args:
        results: List of simulation results
        target_country: Country being analyzed
        show_plot: Whether to display the plot
        save_plot: Whether to save the plot to file
        output_dir: Directory to save charts

    Returns:
        Path to saved chart file or None if not saved.
    """
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))

    colors = ['blue', 'green', 'red']
    for i, result in enumerate(results):
        ax.plot(result['cost_progression'], label=f"Shock to {result['tariff_rate']:.0%}",
                color=colors[i], linewidth=3, marker='o', markersize=6)

    ax.axvline(10, color='red', linestyle='--', alpha=0.7, label='Tariff Shock', linewidth=2)
    ax.set_title(f'Total Cost Impact - {target_country} Tariff Shock\n(Q1 Threshold Method with VAT)',
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
        filename = f"cost_progression_q1_method_{normalize_country_name_for_filename(target_country)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        saved_path = os.path.abspath(filepath)
        print(f"Cost progression chart saved as: {saved_path}")

    if show_plot:
        plt.show()
    else:
        plt.close()

    return saved_path


def create_q1_cost_distribution_chart(simulation: TariffSimulation, tariff_rates: List[float],
                                     target_country: str, show_plot: bool = False,
                                     save_plot: bool = True, output_dir: str = './charts') -> Optional[str]:
    """Create Q1-based cost distribution boxplot chart.

    Shows total system costs after tariff shocks with VAT.

    Args:
        simulation: TariffSimulation instance
        tariff_rates: List of tariff rates to analyze
        target_country: Country being analyzed
        show_plot: Whether to display the plot
        save_plot: Whether to save the plot to file
        output_dir: Directory to save charts

    Returns:
        Path to saved chart file or None if not saved.
    """

    # Calculate cost distributions for each tariff scenario
    cost_distributions = []

    for tariff_rate in tariff_rates:
        # Create temporary tariff rates with the shock applied
        temp_tariffs = simulation.current_tariff_rates.copy()
        temp_tariffs[target_country] = tariff_rate

        # Calculate total system costs for different supplier combinations
        system_costs = []

        # For each product, get all suppliers below Q1 threshold
        product_suppliers = {}
        for product_id in simulation.part_requirements:
            if product_id in simulation.suppliers_by_product:
                suppliers = simulation.suppliers_by_product[product_id]
                quantity = simulation.part_requirements[product_id]

                # Calculate final prices with shock tariffs
                supplier_prices = []
                for supplier in suppliers:
                    cost_info = simulation._calculate_full_cost(
                        supplier['price'],
                        supplier['countryOfOrigin'],
                        product_id,
                        temp_tariffs
                    )
                    supplier_prices.append({
                        'supplier': supplier,
                        'final_price': cost_info['final_price'],
                        'component_cost': cost_info['final_price'] * quantity
                    })

                # Sort and get Q1 threshold
                supplier_prices.sort(key=lambda x: x['final_price'])
                prices_array = np.array([sp['final_price'] for sp in supplier_prices])

                if len(prices_array) == 1:
                    q1_threshold = prices_array[0]
                else:
                    q1_threshold = np.percentile(prices_array, 25)

                # Get suppliers below Q1
                below_q1 = [sp for sp in supplier_prices if sp['final_price'] <= q1_threshold]
                product_suppliers[product_id] = below_q1

        # Generate system cost scenarios by sampling combinations

        # Get supplier options for each product
        supplier_options = []
        for product_id in sorted(product_suppliers.keys()):
            if product_suppliers[product_id]:
                supplier_options.append(product_suppliers[product_id])

        # Generate sample combinations
        max_combinations = 1000
        if supplier_options:
            total_combinations = np.prod([len(options) for options in supplier_options])

            if total_combinations <= max_combinations:
                # Generate all combinations if small enough
                for combination in itertools.product(*supplier_options):
                    total_system_cost = sum(item['component_cost'] for item in combination)
                    system_costs.append(total_system_cost)
            else:
                # Sample random combinations if too many
                random.seed(42)
                for _ in range(max_combinations):
                    combination = [random.choice(options) for options in supplier_options]
                    total_system_cost = sum(item['component_cost'] for item in combination)
                    system_costs.append(total_system_cost)

        # If no combinations possible, use the average Q1 cost
        if not system_costs:
            system_costs = [simulation.get_total_cost(temp_tariffs)]

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
        f'System Cost Distribution - {target_country} Tariff Shock\n(Q1 Threshold Method with VAT)',
        fontweight='bold', fontsize=18)
    ax.set_xlabel('Tariff Rate', fontsize=16)
    ax.set_ylabel('Total Cost (GBP)', fontsize=16)
    ax.grid(True, alpha=0.3)

    # Add summary statistics as text
    for i, (costs, rate) in enumerate(zip(cost_distributions, tariff_rates)):
        if costs:
            stats = {
                'median': np.median(costs),
                'mean': np.mean(costs),
                'max': max(costs),
                'min': min(costs)
            }
            ax.text(i + 1, stats['max'] * 1.02,
                    f"Median: £{stats['median']:.2f}\n"
                    f"Mean: £{stats['mean']:.2f}\n"
                    f"Range: £{stats['min']:.2f}-£{stats['max']:.2f}",
                    ha='center', va='bottom', fontsize=9,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

    # Increase tick label sizes
    ax.tick_params(axis='both', which='major', labelsize=14)
    ax.tick_params(axis='both', which='minor', labelsize=12)

    plt.tight_layout()

    saved_path = None
    if save_plot:
        os.makedirs(output_dir, exist_ok=True)
        filename = f"system_cost_distribution_q1_method_{normalize_country_name_for_filename(target_country)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        saved_path = os.path.abspath(filepath)
        print(f"System cost distribution chart saved as: {saved_path}")

    if show_plot:
        plt.show()
    else:
        plt.close()

    return saved_path


def analyze_tariff_impact(
        suppliers_csv_path: str,
        parts_csv_path: str,
        target_country: str = 'Germany',
        tariff_rates: Optional[List[float]] = None,
        vat_rate: float = 0.20,
        show_plots: bool = False,
        save_plots: bool = True,
        output_dir: str = './charts'
) -> Dict[str, Any]:
    """Analyze tariff impact using Q1 threshold methodology with VAT.

    Args:
        suppliers_csv_path: Path to suppliers CSV file
        parts_csv_path: Path to parts CSV file
        target_country: Country to apply tariff shock to
        tariff_rates: List of tariff rates to test
        vat_rate: VAT rate to apply
        show_plots: Whether to display charts
        save_plots: Whether to save charts
        output_dir: Directory to save output files

    Returns:
        Dictionary containing comprehensive analysis results.
    """

    if tariff_rates is None:
        tariff_rates = [0.10, 0.30, 0.60]

    try:
        suppliers_data, part_requirements, taxable_info = load_data_from_csv(
            suppliers_csv_path, parts_csv_path
        )
    except (FileNotFoundError, ValueError) as e:
        return {'error': f"Failed to load data: {e}"}

    sim = TariffSimulation(suppliers_data, part_requirements, taxable_info, vat_rate)

    # Get current tariff information
    current_tariffs = sim.get_current_tariff_info()
    current_cost_breakdown, current_total_cost = sim.analyze_current_costs()
    q1_analysis = sim.get_q1_analysis()
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
                    'price_increase': shock_cost['final_price'] - current_cost['final_price']
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

    if vat_summary['vat_percentage_of_total'] > 15:
        recommendations.append({
            'type': 'vat_impact',
            'message': f"VAT accounts for {vat_summary['vat_percentage_of_total']:.1f}% of total costs",
            'severity': 'medium'
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

        # Create box and whisker plot (Q1-based cost distribution)
        distribution_chart_path = create_q1_cost_distribution_chart(
            sim, tariff_rates, target_country, show_plots, save_plots, output_dir
        )
        if distribution_chart_path:
            chart_paths['cost_distribution'] = distribution_chart_path

    # Return simplified response
    response = {
        'analysis_type': 'tariff_impact_analysis_with_vat',
        'target_country': target_country,
        'vat_summary': vat_summary,
        'current_cost_analysis': {
            'total_cost': current_total_cost,
        },
        'tariff_scenarios': [
            {
                'tariff_rate': f"{scenario['tariff_rate']:.1%}",
                'cost_impact': {
                    'initial_cost': round(scenario['cost_analysis']['initial_cost'], 2),
                    'final_cost': round(scenario['cost_analysis']['final_cost'], 2),
                    'absolute_increase': round(scenario['cost_analysis']['cost_increase'], 2),
                    'percentage_increase': f"{scenario['cost_analysis']['percentage_increase']:.1f}%"
                },
            }
            for scenario in results
        ],
        'summary': {
            'tariff_rates_tested': tariff_rates,
            'total_suppliers': len(suppliers_data),
            'affected_suppliers': len(results[0]['affected_suppliers']),
            'cost_range': {
                'min_increase': min(r['cost_analysis']['percentage_increase'] for r in results),
                'max_increase': max(r['cost_analysis']['percentage_increase'] for r in results),
                'min_increase_formatted': f"{min(r['cost_analysis']['percentage_increase'] for r in results):.1f}%",
                'max_increase_formatted': f"{max(r['cost_analysis']['percentage_increase'] for r in results):.1f}%"
            },
        },
        'output_files': {
            'chart_paths': chart_paths,
        }
    }

    return response


# Example usage function
def run_example_analysis() -> Dict[str, Any]:
    """Example of how to use the updated simulation with CSV format.

    Returns:
        Analysis results dictionary.
    """

    suppliers_csv = "../core/Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv"
    parts_csv = "../core/Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv"

    result = analyze_tariff_impact(
        suppliers_csv_path=suppliers_csv,
        parts_csv_path=parts_csv,
        target_country='Japan',
        tariff_rates=[0.10, 0.30, 0.60],
        vat_rate=0.20,  # 20% VAT
        show_plots=True,
        save_plots=True
    )

    print(json.dumps(result, indent=2, default=str))
    return result


if __name__ == "__main__":
    # Run the example
    run_example_analysis()