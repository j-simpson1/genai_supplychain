import mesa
from agent import SupplierAgent, ManufacturerAgent

class SupplyChainModel(mesa.Model):
    """Simple supply chain model compatible with Mesa 3.2.0"""

    def __init__(self, seed=None):
        super().__init__(seed=seed)  # Required in Mesa 3.0+

        # Model parameters
        self.base_prices = {
            'screws': {'Germany': 0.08, 'Mexico': 0.06, 'China': 0.04},
            'seat_belts': {'Sweden': 35.00, 'China': 25.00, 'USA': 40.00}
        }
        self.tariffs = {}
        self.parts_inventory = {}

        # Create suppliers
        suppliers_data = [
            ("Bosch", "screws", "Germany"),
            ("Bosch", "screws", "Mexico"),
            ("Autoliv", "seat_belts", "Sweden"),
            ("Autoliv", "seat_belts", "China")
        ]

        for supplier_name, part_type, country in suppliers_data:
            supplier = SupplierAgent(self, supplier_name, part_type, country)
            # Agents are automatically added to self.agents in Mesa 3.0+

        # Create manufacturer
        manufacturer = ManufacturerAgent(
            self,
            required_parts={'screws': 4, 'seat_belts': 1},
            manufacturer_name="Ford",
            preferred_sources={
                'screws': 'Bosch_Germany',
                'seat_belts': 'Autoliv_China'
            }
        )

    def step(self):
        """Model step - activate all agents"""
        # Mesa 3.0+ way: use AgentSet functionality instead of scheduler
        self.agents.shuffle_do("step")


