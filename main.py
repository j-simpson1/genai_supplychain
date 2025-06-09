from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

from data.auto_parts.tecdoc import fetch_categories_data, get_articles_list
from data.auto_parts.transform import parse_categories, transform_data_articles_list
from data.auto_parts.load import load_into_neo4j, insert_article_data_into_neo4j

load_dotenv()
URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")

def get_driver(uri, user, password):
    return GraphDatabase.driver(uri, auth=(user, password))

def main():
    driver = get_driver(URI, USER, PASSWORD)

    # data = fetch_categories_data("140099", "111")
    # nodes, edges = parse_categories(data)
    # load_into_neo4j(nodes, edges)

    article_list = get_articles_list("0 986 495 169")
    transformed_article_list = transform_data_articles_list(article_list)
    insert_article_data_into_neo4j(driver, transformed_article_list)


if __name__ == "__main__":
    main()