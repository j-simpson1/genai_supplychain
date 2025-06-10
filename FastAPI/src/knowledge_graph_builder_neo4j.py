import pandas as pd
from neo4j import GraphDatabase

# Replace with your Aura connection details
NEO4J_URI = "neo4j+s://e9b89a27.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "0zrA7m5k1TYajcEJyT2La942tudU3FVxxxLJHTTVam0"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Load CSV
df = pd.read_csv("../data/knowledge_graph_template.csv")

def create_graph(tx, row):
    tx.run("""
        MERGE (b:Company {name: $buyer})
        MERGE (s:Company {name: $seller})
        MERGE (bl:Location {name: $buyer_loc})
        MERGE (sl:Location {name: $seller_loc})
        MERGE (b)-[:LOCATED_IN]->(bl)
        MERGE (s)-[:LOCATED_IN]->(sl)
        MERGE (b)-[:BUYS_FROM]->(s)
    """, buyer=row['Buyer Legal Entity'],
         seller=row['Current Seller Legal Entity'],
         buyer_loc=row['Buyer LE Location'],
         seller_loc=row['Current Seller LE Location'])

    if pd.notna(row['Alternative Seller Legal Entity 1']):
        tx.run("""
            MERGE (a1:Company {name: $alt1})
            MERGE (b:Company {name: $buyer})
            MERGE (b)-[:CAN_ALSO_BUY_FROM]->(a1)
        """, alt1=row['Alternative Seller Legal Entity 1'],
             buyer=row['Buyer Legal Entity'])

    if pd.notna(row['Alternative Seller Legal Entity 2']):
        tx.run("""
            MERGE (a2:Company {name: $alt2})
            MERGE (b:Company {name: $buyer})
            MERGE (b)-[:CAN_ALSO_BUY_FROM]->(a2)
        """, alt2=row['Alternative Seller Legal Entity 2'],
             buyer=row['Buyer Legal Entity'])

# Run the data import
with driver.session() as session:
    for _, row in df.iterrows():
        session.write_transaction(create_graph, row)

print("Data successfully imported into Aura!")
driver.close()