from mesa import Agent


class SupplierAgent(Agent):
    def __init__(self, unique_id, model, part_type, region):
        super().__init__(unique_id, model)
        self.part_type = part_type
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
    def __init__(self, model, required_parts):
        super().__init__(model)
        self.required_parts = required_parts
        self.cars_built = 0

    def step(self):
        if all(self.model.parts_inventory[part] > 0 for part in self.required_parts):
            for part in self.required_parts:
                self.model.parts_inventory[part] -= 1
            self.cars_built += 1
            print(f"Car built! Total: {self.cars_built}")

class CustomerAgent(Agent):
    def __init__(self, model):
        super().__init__(model)

    def step(self):
        if self.model.manufacturer.cars_built > 0:
            self.model.manufacturer.cars_built -= 1
            print(f"Customer {self.unique_id} bought a car!")