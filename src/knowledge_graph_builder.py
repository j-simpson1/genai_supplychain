import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

# Load CSV
template = pd.read_csv("../data/knowledge_graph_template.csv")

# Create graph
G = nx.MultiDiGraph()

# Main supplier relationships
for _, row in template.iterrows():
    buyer = row['Buyer Legal Entity']
    buyer_loc = row['Buyer LE Location']
    seller = row['Current Seller Legal Entity']
    seller_loc = row['Current Seller LE Location']

    G.add_edge(buyer, seller, relation="buys from")
    G.add_edge(buyer, buyer_loc, relation="located in")
    G.add_edge(seller, seller_loc, relation="located in")

    # Alternative suppliers
    if pd.notna(row['Alternative Seller Legal Entity 1']):
        G.add_edge(buyer, row['Alternative Seller Legal Entity 1'], relation="can also buy from")
    if pd.notna(row['Alternative Seller Legal Entity 2']):
        G.add_edge(buyer, row['Alternative Seller Legal Entity 2'], relation="can also buy from")

# Visualize
pos = nx.spring_layout(G)
edge_labels = {(u, v): d['relation'] for u, v, d in G.edges(data=True)}

nx.draw(G, pos, with_labels=True, node_color='lightblue', node_size=3000, font_size=9)
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=7)
plt.title("Supply Chain Knowledge Graph")
plt.show()