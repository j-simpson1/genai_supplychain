from mesa import Agent


class SupplierAgent(Agent):
    def __init__(self, unique_id, model, part_type, supplier_name, region):
        super().__init__(unique_id, model)
        self.part_type = part_type
        self.supplier_name = supplier_name or f"Supplier-{unique_id}"
        self.region = region

    def get_cost(self):
        base_price = self.model.base_prices[self.part_type][self.region]
        tariff = self.model.tariffs.get(self.region, 0)
        return base_price * (1 + tariff)

    def step(self):
        # Increase inventory count for this region and part
        current_stock = self.model.parts_inventory[self.part_type].get(self.region, 0)
        self.model.parts_inventory[self.part_type][self.region] = current_stock + 1

class ManufacturerAgent(Agent):
    def __init__(self, unique_id, model, required_parts, manufacturer_name, preferred_suppliers):
        super().__init__(unique_id, model)
        self.required_parts = required_parts
        self.components_built = 0
        self.manufacturer_name = manufacturer_name or f"Manufacturer-{unique_id}"
        self.preferred_suppliers = preferred_suppliers

    def calculate_component_cost(self):
        """Calculate total cost for one complete component"""
        total_cost = 0
        for part, supplier_pref in self.preferred_suppliers.items():
            region = supplier_pref["region"]
            # Find the supplier and get their current cost (including tariffs)
            suppliers = [s for s in self.model.schedule.agents_by_type[SupplierAgent]
                         if s.part_type == part and s.region == region]
            if suppliers:
                total_cost += suppliers[0].get_cost()
        return total_cost

    def step(self):
        # Check availability from each preferred supplier and region
        if all(
                self.model.parts_inventory[part].get(pref["region"], 0) > 0
                for part, pref in self.preferred_suppliers.items()
        ):
            for part, pref in self.preferred_suppliers.items():
                region = pref["region"]
                self.model.parts_inventory[part][region] -= 1

            self.components_built += 1
            print(f"{self.manufacturer_name} built component #{self.components_built}")