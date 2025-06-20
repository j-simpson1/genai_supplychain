import mesa
from .agent import SupplierAgent, ManufacturerAgent
import pandas as pd
import heapq
import random


class SupplyChainModel(mesa.Model):
    def __init__(self, supplier_data, seed=None):
        """
        Initialize the supply chain model

        Args:
            supplier_data: DataFrame with parts data (complete bill of materials)
            seed: Random seed for reproducibility
        """
        super().__init__(seed=seed)

        self.base_prices = {}
        self.tariffs = {
            'China': 0.25,
            'Japan': 0.05,
            'Poland': 0.10,
            'Germany': 0.08,
            'United Kingdom': 0.02,
            'France': 0.12
        }
        self.parts_inventory = {}
        self.metrics = {
            "cost_history": [],
            "components_built": [],
            "inventory_levels": [],
            "unused_inventory": [],
            "production_failures": [],
        }
        self.schedule_agents = []
        self.current_step = 0
        self.event_queue = []
        self.event_counter = 0

        # Process the parts data
        self._process_brake_parts_data(supplier_data.copy())

        # Configure manufacturer based on available parts
        self._configure_manufacturer()

    def _configure_manufacturer(self):
        """Configure manufacturer using all available parts (1 of each)"""
        available_parts = list(self.base_prices.keys())
        print(f"Available parts in BOM: {available_parts}")

        required_parts = {}
        preferred_sources = {}

        # Use all available parts, 1 of each
        for part in available_parts:
            supplier_found = False
            if part in self.base_prices:
                for country in self.base_prices[part]:
                    # Find supplier name for this part/country combo
                    for agent in self.schedule_agents:
                        if (isinstance(agent, SupplierAgent) and
                                agent.part_type == part and
                                agent.country == country):
                            preferred_sources[part] = f"{agent.supplier_name}_{country}"
                            required_parts[part] = 1  # Always 1 of each part
                            supplier_found = True
                            break
                    if supplier_found:
                        break

        print(f"Manufacturer configured with {len(required_parts)} parts:")
        for part, qty in required_parts.items():
            source = preferred_sources.get(part, 'Unknown')
            print(f"  - {part} (qty: {qty}) from {source}")

        self.manufacturer = ManufacturerAgent(
            self,
            required_parts=required_parts,
            manufacturer_name="Component_Manufacturer",
            preferred_sources=preferred_sources
        )
        self.schedule_agents.append(self.manufacturer)

    def get_manufacturing_description(self):
        """Get human-readable description of what's being manufactured"""
        return f"Component Assembly (using {len(self.manufacturer.required_parts)} different parts)"

    def _process_brake_parts_data(self, df):
        """Process the brake parts DataFrame to create suppliers and base prices"""

        created_suppliers = set()  # Track created suppliers to avoid duplicates

        for _, row in df.iterrows():
            # Skip rows with missing data
            if pd.isna(row['supplierName']) or pd.isna(row['likelyManufacturingOrigin']):
                continue

            supplier_name = row['supplierName']
            country = row['likelyManufacturingOrigin']
            category_name = row['categoryName']
            price_gbp = row['estimatedPriceGBP']

            # Convert GBP to USD (approximate rate)
            price_usd = price_gbp * 1.27

            # Create supplier key
            supplier_key = f"{supplier_name}_{country}"

            # Store base price (use category name as part type)
            self.base_prices.setdefault(category_name, {})[country] = price_usd

            # Create SupplierAgent if not already created
            if supplier_key not in created_suppliers:
                # Generate realistic lead times based on country
                lead_time = self._get_lead_time_by_country(country)

                supplier = SupplierAgent(
                    self,
                    supplier_name,
                    category_name,
                    country,
                    lead_time,
                    reliability=1.0  # Perfect reliability for all suppliers
                )
                self.schedule_agents.append(supplier)
                created_suppliers.add(supplier_key)

    def _get_lead_time_by_country(self, country):
        """Set fixed lead time for all countries"""
        return 2  # Fixed 2-day lead time for all suppliers

    def step(self):
        """Model step - activate all agents"""
        self.process_events()

        for agent in self.schedule_agents:
            agent.step()

        # Advance time
        self.current_step += 1

        # Record metrics
        self.metrics["cost_history"].append(self.manufacturer.get_component_cost())
        self.metrics["components_built"].append(self.manufacturer.components_built)

        # Inventory snapshot
        self.metrics["inventory_levels"].append(self.parts_inventory.copy())

        # Unused inventory: parts produced but not yet used
        unused_total = sum(self.parts_inventory.values())
        self.metrics["unused_inventory"].append(unused_total)

    def process_events(self):
        """Process all scheduled events at the current time step."""
        while self.event_queue and self.event_queue[0][0] <= self.current_step:
            _, _, event_type, data = heapq.heappop(self.event_queue)

            if event_type == 'delivery':
                key = data['key']
                qty = data['qty']
                self.parts_inventory[key] = self.parts_inventory.get(key, 0) + qty
                print(f"[Step {self.current_step}] Delivered {qty} units of {key}")

    def analyze_supplier_diversity(self):
        """Analyze supplier diversity and geographic risk"""
        supplier_countries = {}
        total_suppliers = 0

        for agent in self.schedule_agents:
            if isinstance(agent, SupplierAgent):
                country = agent.country
                supplier_countries[country] = supplier_countries.get(country, 0) + 1
                total_suppliers += 1

        print("\n=== Supplier Geographic Distribution ===")
        for country, count in sorted(supplier_countries.items()):
            percentage = (count / total_suppliers) * 100
            print(f"{country}: {count} suppliers ({percentage:.1f}%)")

        return supplier_countries