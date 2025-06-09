from data.auto_parts.tecdoc import fetch_categories_data
from data.auto_parts.transform import parse_categories
from data.auto_parts.load import load_into_neo4j



def main():
    data = fetch_categories_data("140099", "111")
    nodes, edges = parse_categories(data)
    print(nodes)
    print(edges)
    load_into_neo4j(nodes, edges)


if __name__ == "__main__":
    main()