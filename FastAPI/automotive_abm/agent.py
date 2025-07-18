import mesa
import random
import heapq


class SupplierAgent(mesa.Agent):
    """Enhanced supplier agent with disruption capabilities"""

    def __init__(self, model, supplier_name, part_type, country, lead_time=2, reliability=1.0):
        super().__init__(model)
        self.supplier_name = supplier_name
        self.part_type = part_type
        self.country = country
        self.base_lead_time = lead_time
        self.lead_time = lead_time
        self.base_reliability = reliability
        self.reliability = reliability

        # Disruption state tracking
        self.is_offline = False
        self.offline_until_step = 0
        self.is_sanctioned = False

    def apply_supplier_disruption(self, offline_duration):
        """Make supplier offline for specified number of steps"""
        self.is_offline = True
        self.offline_until_step = self.model.current_step + offline_duration
        print(
            f"[Step {self.model.current_step}] SUPPLIER OFFLINE: {self.supplier_name} ({self.country}) offline for {offline_duration} steps")

    def apply_sanctions(self):
        """Apply sanctions to this supplier"""
        self.is_sanctioned = True
        print(f"[Step {self.model.current_step}] SANCTIONS APPLIED: {self.supplier_name} ({self.country})")

    def remove_sanctions(self):
        """Remove sanctions from this supplier"""
        self.is_sanctioned = False
        print(f"[Step {self.model.current_step}] SANCTIONS REMOVED: {self.supplier_name} ({self.country})")

    def get_cost(self):
        """Fetch the base price with tariffs and FX adjustments"""
        if self.is_sanctioned:
            return float('inf')  # Cannot trade with sanctioned suppliers

        base_price = self.model.base_prices[self.part_type][self.country]
        tariff = self.model.tariffs.get(self.country, 0)
        fx_rate = self.model.fx_rates.get(self.country, 1.0)

        # Apply tariff and FX rate
        final_price = base_price * (1 + tariff) * fx_rate

        return final_price

    def step(self):
        """Enhanced step method with disruption handling"""
        # Check if supplier comes back online
        if self.is_offline and self.model.current_step >= self.offline_until_step:
            self.is_offline = False
            print(f"[Step {self.model.current_step}] SUPPLIER BACK ONLINE: {self.supplier_name} ({self.country})")

        # Skip production if offline or sanctioned
        if self.is_offline or self.is_sanctioned:
            return

        key = f"{self.part_type}_{self.country}"
        current_stock = self.model.parts_inventory.get(key, 0)
        MAX_INVENTORY = 100

        if current_stock < MAX_INVENTORY:
            if random.random() < self.reliability:
                arrival_step = self.model.current_step + self.lead_time
                self.model.event_counter += 1

                heapq.heappush(self.model.event_queue, (
                    arrival_step,
                    self.model.event_counter,
                    'delivery',
                    {'key': key, 'qty': 10}
                ))
            else:
                print(f"[Step {self.model.current_step}] PRODUCTION FAILURE: {self.supplier_name} ({key})")
                self.model.metrics.setdefault("production_failures", []).append((self.model.current_step, key))
        else:
            print(f"[Step {self.model.current_step}] Skipped production for {key} (inventory {current_stock})")


class ManufacturerAgent(mesa.Agent):
    """Enhanced manufacturer agent with adaptive sourcing"""

    def __init__(self, model, required_parts, manufacturer_name, preferred_sources):
        super().__init__(model)
        self.components_built = 0
        self.manufacturer_name = manufacturer_name
        self.required_parts = required_parts
        self.preferred_sources = preferred_sources.copy()
        self.original_preferred_sources = preferred_sources.copy()

    def adapt_sourcing_strategy(self):
        """Automatically switch to alternative suppliers when preferred ones are unavailable"""
        changes_made = False

        for part_type, current_source in self.preferred_sources.items():
            current_supplier = self.find_supplier(current_source)

            # Check if current supplier is available
            if (not current_supplier or
                    current_supplier.is_offline or
                    current_supplier.is_sanctioned or
                    current_supplier.get_cost() == float('inf')):

                # Find best alternative
                alternatives = self.find_alternatives(part_type)

                for alt in alternatives:
                    alt_supplier = self.find_supplier(alt['key'])
                    if (alt_supplier and
                            not alt_supplier.is_offline and
                            not alt_supplier.is_sanctioned and
                            alt_supplier.get_cost() != float('inf')):
                        old_source = self.preferred_sources[part_type]
                        self.preferred_sources[part_type] = alt['key']

                        print(f"[Step {self.model.current_step}] SOURCING CHANGE: {part_type}")
                        print(f"  FROM: {old_source}")
                        print(f"  TO: {alt['key']} (Cost: ${alt['cost']:.2f})")

                        self.model.metrics.setdefault("sourcing_changes", []).append({
                            'step': self.model.current_step,
                            'part_type': part_type,
                            'from': old_source,
                            'to': alt['key'],
                            'cost': alt['cost']
                        })

                        changes_made = True
                        break

        return changes_made

    def find_supplier(self, supplier_key):
        """Find SupplierAgent object for a given 'name_country' key"""
        if not supplier_key or '_' not in supplier_key:
            return None

        supplier_name, country = supplier_key.split('_', 1)
        for supplier in self.model.schedule_agents:
            if (isinstance(supplier, SupplierAgent) and
                    supplier.supplier_name == supplier_name and
                    supplier.country == country):
                return supplier
        return None

    def find_alternatives(self, part_type):
        """Returns available suppliers for a part, ordered by cost"""
        alternatives = []
        for supplier in self.model.schedule_agents:
            if (isinstance(supplier, SupplierAgent) and
                    supplier.part_type == part_type and
                    not supplier.is_offline and
                    not supplier.is_sanctioned):

                cost = supplier.get_cost()
                if cost != float('inf'):
                    alternatives.append({
                        'key': f"{supplier.supplier_name}_{supplier.country}",
                        'supplier': supplier.supplier_name,
                        'country': supplier.country,
                        'cost': cost
                    })

        return sorted(alternatives, key=lambda x: x['cost'])

    def get_component_cost(self):
        """Calculate total component cost with current sourcing"""
        total_cost = 0
        for part, quantity in self.required_parts.items():
            supplier_key = self.preferred_sources[part]
            supplier = self.find_supplier(supplier_key)
            if supplier:
                cost = supplier.get_cost()
                if cost != float('inf'):
                    total_cost += cost * quantity
                else:
                    return float('inf')  # Cannot build if any part unavailable
        return total_cost

    def analyze_tariff_impact(self, new_tariffs):
        """Calculate the impact of new tariff on production costs"""
        original_tariffs = self.model.tariffs.copy()
        self.model.tariffs.update(new_tariffs)

        results = {}
        total_savings = 0

        for part_type in self.required_parts.keys():
            current_key = self.preferred_sources[part_type]
            current_supplier = self.find_supplier(current_key)

            if current_supplier and current_supplier.country in new_tariffs:
                alternatives = self.find_alternatives(part_type)

                best_alt = None
                for alt in alternatives:
                    if alt['key'] != current_key and alt['country'] not in new_tariffs:
                        best_alt = alt
                        break

                if best_alt:
                    current_cost = current_supplier.get_cost() * self.required_parts[part_type]
                    alt_cost = best_alt['cost'] * self.required_parts[part_type]
                    savings = current_cost - alt_cost

                    results[part_type] = {
                        'current': f"{current_supplier.supplier_name} ({current_supplier.country})",
                        'current_cost': current_cost,
                        'alternative': f"{best_alt['supplier']} ({best_alt['country']})",
                        'alternative_cost': alt_cost,
                        'savings': savings
                    }

                    if savings > 0:
                        total_savings += savings

        self.model.tariffs = original_tariffs

        return {
            'affected_parts': results,
            'total_potential_savings': total_savings
        }

    def step(self):
        """Enhanced step with adaptive sourcing"""
        # First, adapt sourcing strategy if needed
        self.adapt_sourcing_strategy()

        # Then try to build components
        can_build = True
        cost = self.get_component_cost()

        if cost == float('inf'):
            can_build = False
        else:
            # Check inventory availability
            for part, quantity in self.required_parts.items():
                supplier_key = self.preferred_sources[part]
                supplier = self.find_supplier(supplier_key)
                if supplier:
                    inventory_key = f"{part}_{supplier.country}"
                    available = self.model.parts_inventory.get(inventory_key, 0)
                    if available < quantity:
                        can_build = False
                        break
                else:
                    can_build = False
                    break

        if can_build:
            # Consume inventory
            for part, quantity in self.required_parts.items():
                supplier_key = self.preferred_sources[part]
                supplier = self.find_supplier(supplier_key)
                inventory_key = f"{part}_{supplier.country}"
                self.model.parts_inventory[inventory_key] -= quantity

            self.components_built += 1
            print(f"{self.manufacturer_name} built component #{self.components_built} - Cost: ${cost:.2f}")