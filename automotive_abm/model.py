from mesa import Model
from agent import SupplierAgent, ManufacturerAgent, CustomerAgent

class AutomotiveSupplyChain(Model):
    def __init__(self):
        super().__init__()
        self.parts_inventory = {"engine": 0, "chip": 0}

        # Add suppliers - agents are automatically added to model.agents
        supplier1 = SupplierAgent(self, "engine")
        supplier2 = SupplierAgent(self, "chip")

        # Add manufacturer
        self.manufacturer = ManufacturerAgent(self, ["engine", "chip"])

        # Add customers
        for i in range(3):
            customer = CustomerAgent(self)

    def step(self):
        # Use Mesa's built-in agent management - shuffles and calls step() on all agents
        self.agents.shuffle_do("step")