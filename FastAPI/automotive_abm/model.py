import mesa
import heapq
import numpy as np
from FastAPI.automotive_abm.agent import SupplierAgent, ManufacturerAgent


class EnhancedSupplyChainModel(mesa.Model):
    """Enhanced supply chain model with disruption scenario capabilities"""

    def __init__(self, supplier_data, seed=None):
        super().__init__(seed=seed)

        # Initialize base attributes
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
            'Unknown': 0.15
        }

        # FX rates (relative to USD baseline)
        self.fx_rates = {
            'Germany': 1.0,
            'Japan': 1.0,
            'China': 1.0,
            'Poland': 1.0,
            'United Kingdom': 1.0,
            'France': 1.0,
            'Italy': 1.0,
            'USA': 1.0,
            'South Korea': 1.0,
            'Unknown': 1.0
        }

        # FX volatility parameters (daily standard deviation)
        self.fx_volatility = {
            'Germany': 0.02,
            'Japan': 0.03,
            'China': 0.05,
            'Poland': 0.04,
            'United Kingdom': 0.03,
            'France': 0.02,
            'Italy': 0.03,
            'USA': 0.0,  # USD is baseline
            'South Korea': 0.04,
            'Unknown': 0.05
        }

        self.parts_inventory = {}
        self.metrics = {
            "cost_history": [],
            "components_built": [],
            "inventory_levels": [],
            "unused_inventory": [],
            "production_failures": [],
            "sourcing_changes": [],
            "fx_rates_history": [],
            "tariff_history": []
        }

        self.schedule_agents = []
        self.current_step = 0
        self.event_queue = []
        self.event_counter = 0

        # Scenario tracking
        self.active_scenarios = []

        # Process data and configure
        self._process_database_parts_data(supplier_data)
        self._configure_manufacturer()

    def _process_database_parts_data(self, data):
        """Process database data to create enhanced suppliers"""
        created_suppliers = set()
        price_estimates = {}

        for record in data:
            supplier_name = record['supplierName']
            country = record['countryOfOrigin'] or 'Unknown'
            part_description = record['partDescription']
            price = record['price']

            if not supplier_name:
                continue

            if price is None:
                price = self._estimate_price_by_category(part_description, price_estimates)

            price_usd = float(price)
            supplier_key = f"{supplier_name}_{country}"

            # Store base price
            self.base_prices.setdefault(part_description, {})[country] = price_usd

            # Track price for estimation purposes
            if part_description not in price_estimates:
                price_estimates[part_description] = []
            price_estimates[part_description].append(price_usd)

            if supplier_key not in created_suppliers:
                lead_time = self._get_lead_time_by_country(country)

                # Create enhanced SupplierAgent
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
            return 50.0

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
        """Configure manufacturer with enhanced agent"""
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

    # SCENARIO IMPLEMENTATION METHODS

    def apply_supplier_disruption(self, supplier_name, country, duration_steps):
        """Scenario 1: Key supplier goes offline"""
        for agent in self.schedule_agents:
            if (isinstance(agent, SupplierAgent) and
                    agent.supplier_name == supplier_name and
                    agent.country == country):
                agent.apply_supplier_disruption(duration_steps)
                self.active_scenarios.append({
                    'type': 'supplier_disruption',
                    'step': self.current_step,
                    'supplier': f"{supplier_name}_{country}",
                    'duration': duration_steps
                })
                return True
        print(f"Warning: Supplier {supplier_name} ({country}) not found")
        return False

    def apply_tariff_shock(self, country, new_tariff_rate):
        """Scenario 2: Tariff shock from particular country"""
        old_tariff = self.tariffs.get(country, 0)
        self.tariffs[country] = new_tariff_rate

        print(f"[Step {self.current_step}] TARIFF SHOCK: {country} tariff {old_tariff:.1%} → {new_tariff_rate:.1%}")

        self.active_scenarios.append({
            'type': 'tariff_shock',
            'step': self.current_step,
            'country': country,
            'old_tariff': old_tariff,
            'new_tariff': new_tariff_rate
        })

    def apply_sanctions(self, country):
        """Scenario 3: Sanctions against particular country"""
        sanctioned_count = 0
        for agent in self.schedule_agents:
            if isinstance(agent, SupplierAgent) and agent.country == country:
                agent.apply_sanctions()
                sanctioned_count += 1

        if sanctioned_count > 0:
            self.active_scenarios.append({
                'type': 'sanctions',
                'step': self.current_step,
                'country': country,
                'suppliers_affected': sanctioned_count
            })
        else:
            print(f"Warning: No suppliers found in {country} to sanction")

        return sanctioned_count

    def remove_sanctions(self, country):
        """Remove sanctions from a country"""
        removed_count = 0
        for agent in self.schedule_agents:
            if isinstance(agent, SupplierAgent) and agent.country == country and agent.is_sanctioned:
                agent.remove_sanctions()
                removed_count += 1
        return removed_count

    def apply_fx_shock(self, country, new_fx_rate):
        """Apply immediate FX rate shock to a country"""
        old_rate = self.fx_rates.get(country, 1.0)
        self.fx_rates[country] = new_fx_rate

        print(f"[Step {self.current_step}] FX SHOCK: {country} rate {old_rate:.3f} → {new_fx_rate:.3f}")

        self.active_scenarios.append({
            'type': 'fx_shock',
            'step': self.current_step,
            'country': country,
            'old_rate': old_rate,
            'new_rate': new_fx_rate
        })

    def update_fx_rates(self):
        """Scenario 4: FX rate volatility - update rates with random walk"""
        for country in self.fx_rates:
            if country != 'USA':  # USD is baseline
                volatility = self.fx_volatility[country]
                # Random walk with mean reversion
                change = np.random.normal(0, volatility)
                mean_reversion = 0.02 * (1.0 - self.fx_rates[country])  # Pull toward 1.0

                self.fx_rates[country] += change + mean_reversion
                # Keep rates within reasonable bounds (0.5x to 2.0x)
                self.fx_rates[country] = max(0.5, min(2.0, self.fx_rates[country]))

    def set_fx_volatility(self, country, volatility):
        """Set FX volatility for a specific country"""
        if country in self.fx_volatility:
            self.fx_volatility[country] = volatility
            print(f"Set FX volatility for {country} to {volatility:.1%}")

    def get_manufacturing_description(self):
        """Get human-readable description of what's being manufactured"""
        return f"Component Assembly (using {len(self.manufacturer.required_parts)} different parts)"

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

    def get_scenario_summary(self):
        """Get summary of all applied scenarios"""
        return {
            'total_scenarios': len(self.active_scenarios),
            'scenarios': self.active_scenarios
        }

    def get_current_supply_chain_status(self):
        """Get current status of supply chain"""
        status = {
            'offline_suppliers': [],
            'sanctioned_suppliers': [],
            'current_fx_rates': self.fx_rates.copy(),
            'current_tariffs': self.tariffs.copy(),
            'component_cost': self.manufacturer.get_component_cost(),
            'components_built': self.manufacturer.components_built
        }

        for agent in self.schedule_agents:
            if isinstance(agent, SupplierAgent):
                if agent.is_offline:
                    status['offline_suppliers'].append({
                        'supplier': f"{agent.supplier_name}_{agent.country}",
                        'offline_until': agent.offline_until_step
                    })
                if agent.is_sanctioned:
                    status['sanctioned_suppliers'].append(f"{agent.supplier_name}_{agent.country}")

        return status

    def step(self):
        """Enhanced step method with scenario handling"""
        # Update FX rates with volatility
        self.update_fx_rates()

        # Process scheduled events
        self.process_events()

        # Run all agents
        for agent in self.schedule_agents:
            agent.step()

        # Advance time
        self.current_step += 1

        # Record enhanced metrics
        cost = self.manufacturer.get_component_cost()
        self.metrics["cost_history"].append(cost)
        self.metrics["components_built"].append(self.manufacturer.components_built)
        self.metrics["inventory_levels"].append(self.parts_inventory.copy())
        self.metrics["unused_inventory"].append(sum(self.parts_inventory.values()))
        self.metrics["fx_rates_history"].append(self.fx_rates.copy())
        self.metrics["tariff_history"].append(self.tariffs.copy())

    def process_events(self):
        """Process all scheduled events at the current time step"""
        while self.event_queue and self.event_queue[0][0] <= self.current_step:
            _, _, event_type, data = heapq.heappop(self.event_queue)

            if event_type == 'delivery':
                key = data['key']
                qty = data['qty']
                self.parts_inventory[key] = self.parts_inventory.get(key, 0) + qty
                print(f"[Step {self.current_step}] Delivered {qty} units of {key}")