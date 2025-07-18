import csv
from sqlmodel import Session
from FastAPI.database.database import engine
from FastAPI.database.models import Articles  # Ensure your Articles model is imported

# Path to your CSV
CSV_FILE = "pricing_table.csv"

# Open session and execute updates
with Session(engine) as session, open(CSV_FILE, mode='r', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        article_no = row["articleNo"]
        supplier_id = int(row["supplierId"])
        price = float(row["price"])
        price_source = (
            int(row["priceSource"]) if row["priceSource"] and row["priceSource"] != "NULL" else None
        )

        # Fetch the existing article (assumes articleNo is the primary key)
        article = session.get(Articles, (article_no, supplier_id))

        if article:
            article.price = price
            article.priceSource = price_source
        else:
            print(f"Warning: articleNo '{article_no}' not found in DB.")

    session.commit()