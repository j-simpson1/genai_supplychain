import mesa


class SupplierAgent(mesa.Agent):
    def __init__(self, model, supplier_name, part_type, country):
        super().__init__(model)  # Mesa 3.0+ handles unique_id automatically
        self.supplier_name = supplier_name
        self.part_type = part_type
        self.country = country

    def get_cost(self):
        """Get cost including tariffs"""
        base_price = self.model.base_prices[self.part_type][self.country]
        tariff = self.model.tariffs.get(self.country, 0)
        return base_price * (1 + tariff)

    def step(self):
        """Produce parts"""
        key = f"{self.part_type}_{self.country}"
        current = self.model.parts_inventory.get(key, 0)
        self.model.parts_inventory[key] = current + 10


class ManufacturerAgent(mesa.Agent):
    def __init__(self, model, required_parts, manufacturer_name, preferred_sources):
        super().__init__(model)  # Mesa 3.0+ handles unique_id automatically
        self.required_parts = required_parts  # {'screws': 4, 'seat_belts': 1}
        self.components_built = 0
        self.manufacturer_name = manufacturer_name
        self.preferred_sources = preferred_sources  # {'screws': 'Bosch_Germany', 'seat_belts': 'Autoliv_Sweden'}

    def get_component_cost(self):
        """Calculate total component cost"""
        total_cost = 0
        for part, quantity in self.required_parts.items():
            supplier_key = self.preferred_sources[part]
            supplier = self.find_supplier(supplier_key)
            if supplier:
                total_cost += supplier.get_cost() * quantity
        return total_cost

    def find_supplier(self, supplier_key):
        """Find supplier by 'name_country' key"""
        supplier_name, country = supplier_key.split('_')
        for supplier in self.model.agents:
            if (isinstance(supplier, SupplierAgent) and
                    supplier.supplier_name == supplier_name and
                    supplier.country == country):
                return supplier
        return None

    def find_alternatives(self, part_type):
        """Find all suppliers for a part type, sorted by cost"""
        alternatives = []
        for supplier in self.model.agents:
            if isinstance(supplier, SupplierAgent) and supplier.part_type == part_type:
                alternatives.append({
                    'key': f"{supplier.supplier_name}_{supplier.country}",
                    'supplier': supplier.supplier_name,
                    'country': supplier.country,
                    'cost': supplier.get_cost()
                })
        return sorted(alternatives, key=lambda x: x['cost'])

    def analyze_tariff_impact(self, new_tariffs):
        """Calculate tariff impact and find savings"""
        # Save and apply new tariffs
        original_tariffs = self.model.tariffs.copy()
        self.model.tariffs.update(new_tariffs)

        results = {}
        total_savings = 0

        for part_type in self.required_parts.keys():
            current_key = self.preferred_sources[part_type]
            current_supplier = self.find_supplier(current_key)

            if current_supplier and current_supplier.country in new_tariffs:
                alternatives = self.find_alternatives(part_type)

                # Find cheapest alternative not in affected countries
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

        # Restore original tariffs
        self.model.tariffs = original_tariffs

        return {
            'affected_parts': results,
            'total_potential_savings': total_savings
        }

    def step(self):
        """Build components if parts available"""
        can_build = True

        # Check if all parts available
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
            # Consume parts and build
            for part, quantity in self.required_parts.items():
                supplier_key = self.preferred_sources[part]
                supplier = self.find_supplier(supplier_key)
                inventory_key = f"{part}_{supplier.country}"
                self.model.parts_inventory[inventory_key] -= quantity

            self.components_built += 1
            cost = self.get_component_cost()
            print(f"{self.manufacturer_name} built component #{self.components_built} - Cost: ${cost:.2f}")