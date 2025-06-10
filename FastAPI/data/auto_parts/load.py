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


def insert_article_data_into_neo4j(driver, data):
    try:
        with driver.session() as session:
            # Suppliers
            for s in data['suppliers']:
                session.run("""
                    MERGE (sup:Supplier {supplierId: $supplierId})
                    SET sup.name = $supplierName
                """, s)

            # Articles and Supplier relationship
            for a in data['articles']:
                session.run("""
                    MERGE (a:Article {articleId: $articleId})
                    SET a.articleNo = $articleNo,
                        a.productName = $productName,
                        a.image = $image
                    WITH a
                    MATCH (s:Supplier {supplierId: $supplierId})
                    MERGE (a)-[:SUPPLIED_BY]->(s)
                """, a)

            # Specifications
            for spec in data['specifications']:
                session.run("""
                    MERGE (s:Specification {specId: $specId})
                    SET s.name = $name,
                        s.value = $value
                """, spec)

            for rel in data['article_spec_rel']:
                session.run("""
                    MATCH (a:Article {articleId: $articleId})
                    MATCH (s:Specification {specId: $specId})
                    MERGE (a)-[:HAS_SPECIFICATION]->(s)
                """, rel)

            # OEMs
            for oem in data['oems']:
                session.run("""
                    MERGE (o:OEM {oemId: $oemId})
                    SET o.brand = $brand,
                        o.displayNo = $displayNo
                """, oem)

            for rel in data['article_oem_rel']:
                session.run("""
                    MATCH (a:Article {articleId: $articleId})
                    MATCH (o:OEM {oemId: $oemId})
                    MERGE (a)-[:HAS_OEM]->(o)
                """, rel)

            # Vehicles
            for v in data['vehicles']:
                session.run("""
                    MERGE (v:Vehicle {vehicleId: $vehicleId})
                    SET v.modelId = $modelId,
                        v.manufacturerName = $manufacturerName,
                        v.modelName = $modelName,
                        v.typeEngineName = $typeEngineName,
                        v.start = $constructionIntervalStart,
                        v.end = $constructionIntervalEnd
                """, v)

            for rel in data['article_vehicle_rel']:
                session.run("""
                    MATCH (a:Article {articleId: $articleId})
                    MATCH (v:Vehicle {vehicleId: $vehicleId})
                    MERGE (a)-[:COMPATIBLE_WITH]->(v)
                """, rel)
        print("Article data successfully loaded into Neo4j.")
    except Exception as e:
        print(f"Error loading article data into Neo4j: {e}")