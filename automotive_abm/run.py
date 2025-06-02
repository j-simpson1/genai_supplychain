from model import AutomotiveSupplyChain

model = AutomotiveSupplyChain()

for i in range(10):
    print(f"\n--- Step {i+1} ---")
    model.step()