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

            # Store base price
            self.base_prices.setdefault(part_type, {})[country] = price

            # Create agent
            supplier = SupplierAgent(self, supplier_name, part_type, country)

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

    def step(self):
        """Model step - activate all agents"""
        # Mesa 3.0+ way: use AgentSet functionality instead of scheduler
        self.agents.shuffle_do("step")


