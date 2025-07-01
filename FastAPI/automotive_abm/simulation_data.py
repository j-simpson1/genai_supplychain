from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import text
from FastAPI.database.database import DATABASE_URL, engine

# Your query (note: no trailing semicolon)
query = text("""
SELECT
    p."productGroupId",
    p."description" AS "partDescription",
    p."categoryId",
    c."description" AS "categoryDescription",
    a."articleNo",
    a."articleProductName",
    a."price",
    a."countryOfOrigin",
    s."supplierId",
    s."supplierName"
FROM
    "parts" AS p
INNER JOIN "articlevehiclelink" AS avl
    ON p."productGroupId" = avl."productGroupId"
INNER JOIN "articles" AS a
    ON avl."articleNo" = a."articleNo"
    AND avl."supplierId" = a."supplierId"
INNER JOIN "suppliers" AS s
    ON a."supplierId" = s."supplierId"
INNER JOIN "category" AS c
    ON p."categoryId" = c."categoryId"
""")

# Open session and execute
with Session(engine) as session:
    result = session.exec(query)
    rows = result.fetchall()

# Convert rows to list of dicts
columns = result.keys()
data = [dict(zip(columns, row)) for row in rows]

# Display or process
for record in data:
    print(record)