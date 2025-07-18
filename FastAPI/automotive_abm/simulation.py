import matplotlib.pyplot as plt
import numpy as np
import json
from collections import defaultdict


class TariffSimulation:
    """Simplified tariff simulation using real brake parts data"""

    def __init__(self, suppliers_data, part_requirements):
        self.suppliers_data = suppliers_data
        self.part_requirements = part_requirements
        self.suppliers_by_product = self._group_suppliers()
        self.current_suppliers = self._get_cheapest_suppliers()
        self.cost_history = []

    def _group_suppliers(self):
        """Group suppliers by product ID"""
        groups = defaultdict(list)
        for supplier in self.suppliers_data:
            groups[supplier['productId']].append(supplier)
        return groups

    def _get_cheapest_suppliers(self, tariffs=None):
        """Find cheapest supplier for each required product"""
        if tariffs is None:
            tariffs = {}

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
            tariffs = {}

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
        current_tariffs = {}

        for step in range(steps):
            if step == shock_step:
                current_tariffs[target_country] = tariff_rate
                self.current_suppliers = self._get_cheapest_suppliers(current_tariffs)

            cost = self.get_total_cost(current_tariffs)
            self.cost_history.append(cost)

        return {
            'initial_cost': self.cost_history[0],
            'final_cost': self.cost_history[-1],
            'cost_increase': self.cost_history[-1] - self.cost_history[0]
        }


def load_sample_data():
    """Load sample brake parts data"""
    suppliers_data = [
        {'articleNo': '0088', 'articleProductName': 'Bleeder Screw/Valve', 'productId': 5213, 'price': 0.96,
         'countryOfOrigin': 'Denmark', 'supplierName': 'QUICK BRAKE'},
        {'articleNo': '0101-GSV70F', 'articleProductName': 'Brake Pad Set', 'productId': 402, 'price': 4.08,
         'countryOfOrigin': 'Japan', 'supplierName': 'FEBEST'},
        {'articleNo': '0101-GYL25R', 'articleProductName': 'Brake Pad Set', 'productId': 402, 'price': 18.52,
         'countryOfOrigin': 'Japan', 'supplierName': 'FEBEST'},
        {'articleNo': '08.D418.11', 'articleProductName': 'Brake Disc', 'productId': 82, 'price': 34.66,
         'countryOfOrigin': 'Netherlands', 'supplierName': 'A.B.S.'},
        {'articleNo': '0 986 424 899', 'articleProductName': 'Brake Pad Set', 'productId': 402, 'price': 48.51,
         'countryOfOrigin': 'Germany', 'supplierName': 'BOSCH'},
        {'articleNo': '0 986 424 912', 'articleProductName': 'Brake Pad Set', 'productId': 402, 'price': 24.64,
         'countryOfOrigin': 'Germany', 'supplierName': 'BOSCH'},
        {'articleNo': '0 986 479 E91', 'articleProductName': 'Brake Disc', 'productId': 82, 'price': 10.46,
         'countryOfOrigin': 'Germany', 'supplierName': 'BOSCH'},
        {'articleNo': '0 986 479 H04', 'articleProductName': 'Brake Disc', 'productId': 82, 'price': 10.46,
         'countryOfOrigin': 'Germany', 'supplierName': 'BOSCH'},
        {'articleNo': '09.D979.11', 'articleProductName': 'Brake Disc', 'productId': 82, 'price': 54.47,
         'countryOfOrigin': 'Italy', 'supplierName': 'BREMBO'},
        {'articleNo': '13012145281', 'articleProductName': 'Brake Caliper', 'productId': 78, 'price': 102.57,
         'countryOfOrigin': 'Denmark', 'supplierName': 'sbs'},
        {'articleNo': '13012145282', 'articleProductName': 'Brake Caliper', 'productId': 78, 'price': 102.57,
         'countryOfOrigin': 'Denmark', 'supplierName': 'sbs'},
        {'articleNo': '2145281', 'articleProductName': 'Brake Caliper', 'productId': 78, 'price': 49.36,
         'countryOfOrigin': 'Denmark', 'supplierName': 'NK'},
        {'articleNo': '740581', 'articleProductName': 'Brake Caliper', 'productId': 78, 'price': 61.63,
         'countryOfOrigin': 'Netherlands', 'supplierName': 'A.B.S.'},
        {'articleNo': '19000', 'articleProductName': 'Brake Fluid', 'productId': 3357, 'price': 65.59,
         'countryOfOrigin': 'Netherlands', 'supplierName': 'MPM'},
        {'articleNo': '20000_', 'articleProductName': 'Brake Fluid', 'productId': 3357, 'price': 4.04,
         'countryOfOrigin': 'Netherlands', 'supplierName': 'MPM'},
        {'articleNo': 'DOT3', 'articleProductName': 'Brake Fluid', 'productId': 3357, 'price': 8.26,
         'countryOfOrigin': 'Netherlands', 'supplierName': 'KROON OIL'},
        {'articleNo': 'DOT4', 'articleProductName': 'Brake Fluid', 'productId': 3357, 'price': 3.48,
         'countryOfOrigin': 'Netherlands', 'supplierName': 'KROON OIL'},
    ]

    part_requirements = {402: 1, 82: 2, 78: 2, 3357: 1, 5213: 4}
    return suppliers_data, part_requirements


def analyze_tariff_impact(target_country='Germany', show_plots=True):
    """Analyze 10%, 30%, and 60% tariff impact and return JSON"""

    suppliers_data, part_requirements = load_sample_data()
    tariff_rates = [0.10, 0.30, 0.60]

    results = []
    price_distributions = []

    for rate in tariff_rates:
        sim = TariffSimulation(suppliers_data, part_requirements)
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
                    'original_price': supplier['price'],
                    'adjusted_price': adjusted_price,
                    'price_increase': adjusted_price - supplier['price']
                })
                all_prices.append(adjusted_price)
            else:
                all_prices.append(supplier['price'])

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

    # Create visualization if requested
    if show_plots:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        # Cost progression
        colors = ['blue', 'green', 'red']
        for i, result in enumerate(results):
            ax1.plot(result['cost_progression'], label=f"{result['tariff_rate']:.0%}",
                     color=colors[i], linewidth=2, marker='o', markersize=3)

        ax1.axvline(10, color='red', linestyle='--', alpha=0.7, label='Tariff Shock')
        ax1.set_title(f'Cost Impact - {target_country} Tariff', fontweight='bold')
        ax1.set_xlabel('Time Step')
        ax1.set_ylabel('Total Cost (USD)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Box plot
        box_colors = ['lightblue', 'lightgreen', 'lightcoral']
        box_plot = ax2.boxplot(price_distributions, labels=[f'{r:.0%}' for r in tariff_rates],
                               patch_artist=True)

        for patch, color in zip(box_plot['boxes'], box_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        ax2.set_title(f'Price Distribution - {target_country} Tariff', fontweight='bold')
        ax2.set_xlabel('Tariff Rate')
        ax2.set_ylabel('Article Price (USD)')
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

    # Return JSON response
    return {
        'analysis_type': 'tariff_impact_analysis',
        'target_country': target_country,
        'timestamp': '2025-07-18T16:24:22.000Z',
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
        'recommendations': recommendations
    }


if __name__ == "__main__":
    # Standard analysis with plots
    print("Running tariff impact analysis...")
    result = analyze_tariff_impact('Germany', show_plots=True)

    # LangGraph JSON output
    print("\n" + "=" * 50)
    print("JSON OUTPUT FOR LANGGRAPH:")
    print("=" * 50)

    json_output = analyze_tariff_impact('Germany', show_plots=False)
    print(json.dumps(json_output, indent=2))