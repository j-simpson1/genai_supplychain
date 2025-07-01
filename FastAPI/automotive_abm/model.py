import mesa
from FastAPI.automotive_abm.agent import SupplierAgent, ManufacturerAgent
import heapq


class SupplyChainModel(mesa.Model):
    def __init__(self, supplier_data, seed=None):
        """
        Initialize the supply chain model

        Args:
            supplier_data: List of dictionaries from database query
            seed: Random seed for reproducibility
        """
        super().__init__(seed=seed)

        self.base_prices = {}
        self.tariffs = {
            'Germany': 0.08,
            'Japan': 0.05,
            'China': 0.25,
            'Poland': 0.10,
            'United Kingdom': 0.02,
            'France': 0.12,
            'Italy': 0.07,
            'USA': 0.00,
            'South Korea': 0.06,
            'Unknown': 0.15  # Default tariff for unknown countries
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

        # Process the database data
        self._process_database_parts_data(supplier_data)

        # Configure manufacturer based on available parts
        self._configure_manufacturer()

    def _process_database_parts_data(self, data):
        """Process the database query results to create suppliers and base prices"""

        created_suppliers = set()
        price_estimates = {}  # Track price estimates for missing prices

        for record in data:
            supplier_name = record['supplierName']
            country = record['countryOfOrigin'] or 'Unknown'  # Handle None values
            part_description = record['partDescription']
            price = record['price']

            # Skip records with missing supplier name
            if not supplier_name:
                continue

            # Handle missing prices - estimate based on category
            if price is None:
                price = self._estimate_price_by_category(part_description, price_estimates)

            # Convert price to USD if needed (assuming input is in appropriate currency)
            price_usd = float(price)

            # Create supplier key
            supplier_key = f"{supplier_name}_{country}"

            # Store base price (use part description as part type)
            self.base_prices.setdefault(part_description, {})[country] = price_usd

            # Track price for estimation purposes
            if part_description not in price_estimates:
                price_estimates[part_description] = []
            price_estimates[part_description].append(price_usd)

            # Create SupplierAgent if not already created
            if supplier_key not in created_suppliers:
                lead_time = self._get_lead_time_by_country(country)

                supplier = SupplierAgent(
                    self,
                    supplier_name,
                    part_description,
                    country,
                    lead_time,
                    reliability=1.0
                )
                self.schedule_agents.append(supplier)
                created_suppliers.add(supplier_key)

        print(f"Created {len(created_suppliers)} unique suppliers")
        print(f"Processing {len(self.base_prices)} part types")

    def _estimate_price_by_category(self, part_description, price_estimates):
        """Estimate price for parts with missing price data"""
        # Default prices by part category (in USD)
        default_prices = {
            'Brake Caliper': 85.0,
            'Brake Caliper Mounting': 45.0,
            'Brake Master Cylinder': 65.0,
            'Brake Booster': 120.0,
            'Wheel Cylinders': 25.0,
            'Brake Pads': 35.0,
            'Brake Discs': 55.0,
            'Brake Drum': 45.0,
            'Brake Hose': 15.0,
            'Brake Fluid': 8.0,
            'Brake Caliper Parts': 30.0,
            'Brake System': 40.0
        }

        # If we have existing prices for this category, use average
        if part_description in price_estimates and price_estimates[part_description]:
            return sum(price_estimates[part_description]) / len(price_estimates[part_description])

        # Otherwise use default or estimate based on part name
        for category, price in default_prices.items():
            if category.lower() in part_description.lower():
                return price

        # Final fallback - estimate based on keywords
        part_lower = part_description.lower()
        if any(word in part_lower for word in ['caliper', 'cylinder', 'master']):
            return 75.0
        elif any(word in part_lower for word in ['pad', 'disc', 'drum']):
            return 45.0
        elif any(word in part_lower for word in ['hose', 'fluid', 'sensor']):
            return 20.0
        else:
            return 50.0  # Generic fallback

    def _get_lead_time_by_country(self, country):
        """Set lead time based on country distance/logistics"""
        lead_times = {
            'Germany': 2,
            'France': 2,
            'Italy': 3,
            'Poland': 3,
            'United Kingdom': 2,
            'Japan': 7,
            'China': 14,
            'South Korea': 10,
            'USA': 5,
            'Unknown': 5
        }
        return lead_times.get(country, 5)

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
                # Find the cheapest supplier for each part initially
                cheapest_country = min(self.base_prices[part].keys(),
                                       key=lambda c: self.base_prices[part][c])

                # Find supplier name for this part/country combo
                for agent in self.schedule_agents:
                    if (isinstance(agent, SupplierAgent) and
                            agent.part_type == part and
                            agent.country == cheapest_country):
                        preferred_sources[part] = f"{agent.supplier_name}_{cheapest_country}"
                        required_parts[part] = 1
                        supplier_found = True
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