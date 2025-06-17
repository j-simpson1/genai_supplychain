import random

def select_preferred_article(articles, ranked_suppliers):
    # Ensure ranked_suppliers has correct structure
    if not isinstance(ranked_suppliers, dict):
        print("Warning: ranked_suppliers is not a dictionary")
        ranked_suppliers = {
            "first_choice": [],
            "second_choice": []
        }

    first_choice = ranked_suppliers.get("first_choice", [])
    second_choice = ranked_suppliers.get("second_choice", [])

    # Try to find article from first_choice suppliers
    for article in articles:
        if article["supplierName"] in first_choice:
            return article, "first_choice"

    # Try to find article from second_choice suppliers
    for article in articles:
        if article["supplierName"] in second_choice:
            return article, "second_choice"

    # If no preferred supplier found, return a random article
    if articles:
        random_article = random.choice(articles)
        return random_article, "other"

    # No articles available
    return None, None