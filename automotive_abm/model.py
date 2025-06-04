import mesa
from agent import SupplierAgent, ManufacturerAgent
import pandas as pd
import json


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
        self.in_transit_inventory = {}  # key: part_country -> list of (arrival_step, quantity)
        self.current_step = 0

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

        # Deliver arriving shipments
        for key, queue in self.in_transit_inventory.items():
            arrivals = [q for q in queue if q[0] <= self.current_step]
            still_waiting = [q for q in queue if q[0] > self.current_step]

            if arrivals:
                total_arrived = sum(q[1] for q in arrivals)
                self.parts_inventory[key] = self.parts_inventory.get(key, 0) + total_arrived
                print(f"[Step {self.current_step}] Delivered {total_arrived} units of {key}")

            self.in_transit_inventory[key] = still_waiting

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

    def get_expected_inventory(self, key):
        current_stock = self.parts_inventory.get(key, 0)
        in_transit = sum(qty for (step, qty) in self.in_transit_inventory.get(key, []))
        return current_stock + in_transit


