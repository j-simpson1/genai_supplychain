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
        return base_price * ((1 + tariff) / 1)

    def step(self):
        # Increase inventory count for this region and part
        current_stock = self.model.parts_inventory[self.part_type].get(self.region, 0)
        self.model.parts_inventory[self.part_type][self.region] = current_stock + 1

class ManufacturerAgent(Agent):
    def __init__(self, unique_id, model, required_parts, manufacturer_name):
        super().__init__(unique_id, model)
        self.required_parts = required_parts
        self.components_built = 0
        self.manufacturer_name = manufacturer_name or f"Manufacturer-{unique_id}"

    def step(self):
        if all(self.model.parts_inventory[pid] > 0 for pid in self.required_parts):
            for pid in self.required_parts:
                self.model.parts_inventory[pid] -= 1
            self.components_built += 1
            print(f"{self.manufacturer_name} built component #{self.components_built}")