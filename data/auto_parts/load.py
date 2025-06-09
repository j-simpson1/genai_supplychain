from neo4j import GraphDatabase
from dotenv import load_dotenv
import os


load_dotenv()
# Set up connection to Neo4j instance
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

# Create or update a Category node using MERGE (ensures uniqueness by id)
def create_node(tx, node_id, text):
    tx.run(
        """
        MERGE (c:Category {id: $id})
        SET c.text = $text
        """,
        id=node_id, text=text
    )

# Create a HAS_CHILD relationship between two Category nodes by id
def create_edge(tx, from_id, to_id):
    tx.run(
        """
        MATCH (parent:Category {id: $from_id})
        MATCH (child:Category {id: $to_id})
        MERGE (parent)-[:HAS_CHILD]->(child)
        """,
        from_id=from_id, to_id=to_id
    )

# Load nodes and edges into Neo4j using write transactions
def load_into_neo4j(nodes, edges):
    try:
        with driver.session() as session:
            for node in nodes:
                session.execute_write(create_node, node['id'], node['text'])
            for edge in edges:
                session.execute_write(create_edge, edge['from'], edge['to'])
        print("Data loaded into Neo4j successfully.")
    except Exception as e:
        print(f"Error loading data into Neo4j: {e}")