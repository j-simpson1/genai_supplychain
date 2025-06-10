import mesa
from agent import SupplierAgent, ManufacturerAgent
import pandas as pd
import json
import heapq


class SupplyChainModel(mesa.Model):
    def __init__(self, supplier_csv_path="../data/dummy_braking_system_bom.csv", seed=None):
        super().__init__(seed=seed)

        self.base_prices = {}
        self.tariffs = {}
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

        # Load average tariff data from JSON
        with open("../data/tariff_data/avg_tariff_dict.json", "r") as f:
            avg_tariff_data = json.load(f)

        # Convert % tariffs to decimal form
        self.tariffs = {country: rate / 100 for country, rate in avg_tariff_data.items()}

        # Load dummy data
        df = pd.read_csv(supplier_csv_path)

        # Build base_prices dictionary and create SupplierAgents
        for _, row in df.iterrows():
            part_type = row["Component"]
            country = row["Country"]
            price = row["Price (USD)"]
            supplier_name = row["Supplier No."]
            lead_time = int(row["Lead Time (days)"])
            reliability = float(row["Reliability"])

            # Store base price
            self.base_prices.setdefault(part_type, {})[country] = price

            # Create agent
            supplier = SupplierAgent(self, supplier_name, part_type, country, lead_time, reliability)
            self.schedule_agents.append(supplier)

        # Define a manufacturer using some components (customize this as needed)
        self.manufacturer = ManufacturerAgent(
            self,
            required_parts={
                "Brake Pad (Front)": 2,
                "Brake Disc (Front)": 2,
                "Brake Caliper": 2
            },
            manufacturer_name="Ford",
            preferred_sources={
                "Brake Pad (Front)": "SUP-1001_Germany",
                "Brake Disc (Front)": "SUP-1201_Mexico",
                "Brake Caliper": "SUP-1001_Germany"
            }
        )
        self.schedule_agents.append(self.manufacturer)

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

        # Inventory snapshot
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


