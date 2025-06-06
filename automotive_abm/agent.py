import mesa
import random
import heapq


class SupplierAgent(mesa.Agent):
    """Companies that produce specifics automotive parts such as screws and seat belts."""
    def __init__(self, model, supplier_name, part_type, country, lead_time=2, reliability=1.0):
        super().__init__(model)  # Note Mesa 3.0+ handles unique_id automatically
        self.supplier_name = supplier_name
        self.part_type = part_type
        self.country = country
        self.lead_time = lead_time
        self.reliability = reliability

    def get_cost(self):
        """Fetch the base price of the parts with country-specific tariffs applied"""
        base_price = self.model.base_prices[self.part_type][self.country]
        tariff = self.model.tariffs.get(self.country, 0)
        return base_price * (1 + tariff)

    def step(self):
        """Each simulation step for the Supplier"""
        key = f"{self.part_type}_{self.country}"
        current_stock = self.model.parts_inventory.get(key, 0)
        MAX_INVENTORY = 100

        # First checks the stock is below the set level of MAX_INVENTORY
        if current_stock < MAX_INVENTORY:
            # If it is then a shipment of 10 units is created with a probability in line with the suppliers reliability
            # It is scheduled to arrive after lead_time steps
            if random.random() < self.reliability:
                arrival_step = self.model.current_step + self.lead_time
                self.model.event_counter += 1  # Increment unique event counter

                heapq.heappush(self.model.event_queue, (
                    arrival_step,  # Priority 1: delivery time
                    self.model.event_counter,  # Priority 2: unique tiebreaker
                    'delivery',  # Event type
                    {'key': key, 'qty': 10}  # Event data
                ))
            else:
                print(f"[Step {self.model.current_step}] PRODUCTION FAILURE: {self.supplier_name} ({key})")
                self.model.metrics.setdefault("production_failures", []).append((self.model.current_step, key))
        else:
            print(f"[Step {self.model.current_step}] Skipped production for {key} (inventory {current_stock})")


class ManufacturerAgent(mesa.Agent):
    def __init__(self, model, required_parts, manufacturer_name, preferred_sources):
        super().__init__(model)  # Note Mesa 3.0+ handles unique_id automatically
        self.components_built = 0
        self.manufacturer_name = manufacturer_name
        # required_parts and preferred_sources are set in the models file, currently using dummy data.
        self.required_parts = required_parts  # e.g. {'screws': 4, 'seat_belts': 1}
        self.preferred_sources = preferred_sources  # e.g. {'screws': 'Bosch_Germany', 'seat_belts': 'Autoliv_Sweden'}

    def get_component_cost(self):
        """Calculate total component cost taking into account the preferred suppliers and the current tariff rates"""
        total_cost = 0
        for part, quantity in self.required_parts.items():
            supplier_key = self.preferred_sources[part]
            supplier = self.find_supplier(supplier_key)
            if supplier:
                total_cost += supplier.get_cost() * quantity
        return total_cost

    def find_supplier(self, supplier_key):
        """Find supplierAgent object for a given 'name_country' key"""
        supplier_name, country = supplier_key.split('_')
        for supplier in self.model.schedule_agents:
            if (isinstance(supplier, SupplierAgent) and
                    supplier.supplier_name == supplier_name and
                    supplier.country == country):
                return supplier
        return None

    def find_alternatives(self, part_type):
        """Returns a list of all available suppliers for a given part, ordered by cost (including tariffs)"""
        alternatives = []
        for supplier in self.model.schedule_agents:
            if isinstance(supplier, SupplierAgent) and supplier.part_type == part_type:
                alternatives.append({
                    'key': f"{supplier.supplier_name}_{supplier.country}",
                    'supplier': supplier.supplier_name,
                    'country': supplier.country,
                    'cost': supplier.get_cost()
                })
        return sorted(alternatives, key=lambda x: x['cost'])

    def analyze_tariff_impact(self, new_tariffs):
        """Calculate the impact of new tariff on production costs"""
        original_tariffs = self.model.tariffs.copy()
        self.model.tariffs.update(new_tariffs)

        results = {}
        total_savings = 0

        for part_type in self.required_parts.keys():
            current_key = self.preferred_sources[part_type]
            current_supplier = self.find_supplier(current_key)

            # check if the current supplier is a newly tariffed country
            if current_supplier and current_supplier.country in new_tariffs:
                alternatives = self.find_alternatives(part_type)

                # if yes find the cheapest alternative supplier not in a tariffed country
                best_alt = None
                for alt in alternatives:
                    if alt['key'] != current_key and alt['country'] not in new_tariffs:
                        best_alt = alt
                        break

                if best_alt:
                    # calculate and store potential cost savings by switching supplier
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

        # Restore original tariffs
        self.model.tariffs = original_tariffs

        # Return dictionary of effected parts with cost comparison, showing the potential savings from
        # switching supplier
        return {
            'affected_parts': results,
            'total_potential_savings': total_savings
        }

    def step(self):
        """Each simulation step for the manufacturers - build the components if parts available"""
        can_build = True

        # Checks whether the current inventory holds enough of each required part to build the component
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
            # if sufficient parts in inventory then those parts are consumed
            for part, quantity in self.required_parts.items():
                supplier_key = self.preferred_sources[part]
                supplier = self.find_supplier(supplier_key)
                inventory_key = f"{part}_{supplier.country}"
                self.model.parts_inventory[inventory_key] -= quantity

            # count of built components is incremented by 1
            self.components_built += 1
            cost = self.get_component_cost()
            # cost of the component built is printed out to the terminal
            print(f"{self.manufacturer_name} built component #{self.components_built} - Cost: ${cost:.2f}")