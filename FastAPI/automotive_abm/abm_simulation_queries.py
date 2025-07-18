import pandas as pd
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import text
from FastAPI.database.database import engine

def parts(engine):

    query_text = """
    SELECT DISTINCT
        p."productGroupId",
        p."description" AS "partDescription"
    FROM
        "parts" p
    INNER JOIN "articlevehiclelink" avl
        ON p."productGroupId" = avl."productGroupId"
    INNER JOIN "articles" a
        ON avl."articleNo" = a."articleNo"
        AND avl."supplierId" = a."supplierId"
    """

    query = text(query_text)

    with Session(engine) as session:
        result = session.exec(query)
        rows = result.fetchall()

        # Convert rows to list of dicts
        columns = result.keys()
        data = [dict(zip(columns, row)) for row in rows]

    return data

def parts(engine):

    query_text = """
    SELECT DISTINCT
        p."productGroupId",
        p."description" AS "partDescription"
    FROM
        "parts" p
    INNER JOIN "articlevehiclelink" avl
        ON p."productGroupId" = avl."productGroupId"
    INNER JOIN "articles" a
        ON avl."articleNo" = a."articleNo"
        AND avl."supplierId" = a."supplierId"
    """

    query = text(query_text)

    with Session(engine) as session:
        result = session.exec(query)
        rows = result.fetchall()

        # Convert rows to list of dicts
        columns = result.keys()
        data = [dict(zip(columns, row)) for row in rows]

    return data

def articles(engine):

    query_text = """
    SELECT
        a."articleNo",
        a."articleProductName",
        a."productId",
        a."price",
        a."supplierId",
        a."countryOfOrigin",
        s."supplierName"
    FROM
        "articles" a
    INNER JOIN "suppliers" s
        ON a."supplierId" = s."supplierId"
    ORDER BY
        a."articleNo";
    """

    query = text(query_text)

    with Session(engine) as session:
        result = session.exec(query)
        rows = result.fetchall()

        # Convert rows to list of dicts
        columns = result.keys()
        data = [dict(zip(columns, row)) for row in rows]

    return data

print(parts(engine))
print(articles(engine))

