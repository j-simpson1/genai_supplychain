from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import text
from FastAPI.database.database import engine

from FastAPI.database.models import Articles
from FastAPI.data.auto_parts.autodoc_search import search_autodoc
import time
import random

def retrieve_all_articles(engine, query_text=None):

    if query_text is None:
        # Default query matching your example
        query_text = """
        SELECT *
        FROM "articles" a
        ORDER BY a."articleNo", a."supplierId"
        """

    query = text(query_text)

    with Session(engine) as session:
        result = session.exec(query)
        rows = result.fetchall()

        # Convert rows to list of dicts
        columns = result.keys()
        data = [dict(zip(columns, row)) for row in rows]

    return data


def get_pricing_data(all_articles):
    gbp_eur_fx_rate = 1.16
    output = []

    for article in all_articles[283:285]:
        articleNo = article['articleNo']
        supplierId = article['supplierId']
        price_search = search_autodoc(articleNo)
        if price_search and price_search['results']:
            first_price = round(price_search['results'][0]['price'] / gbp_eur_fx_rate, 2)
            article['price'] = first_price
            article['priceSource'] = 1
            print(f"articleNo: {articleNo}, supplierId: {supplierId}, price: {first_price}, priceSource: 1")
            output.append({'articleNo': articleNo, 'supplierId': supplierId, 'price': first_price, 'priceSource': 1})
        time.sleep(random.uniform(1, 2))

    with Session(engine) as session:
        for item in output:
            db_article = session.get(Articles, (item['articleNo'], item['supplierId']))
            if db_article:
                db_article.price = item['price']
                db_article.priceSource = item['priceSource']
        session.commit()

all_articles = retrieve_all_articles(engine)
get_pricing_data(all_articles)