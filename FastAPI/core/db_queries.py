from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import text
from FastAPI.database.database import engine

def fetch_parts_count_by_supplier(engine):

    query_text = """
    SELECT
        s."supplierId",
        s."supplierName",
        COUNT(*) AS parts_count
    FROM
        "articles" AS a
    INNER JOIN "suppliers" AS s
        ON a."supplierId" = s."supplierId"
    GROUP BY
        s."supplierId",
        s."supplierName"
    ORDER BY
        parts_count DESC;
    """

    query = text(query_text)

    with Session(engine) as session:
        result = session.exec(query)
        rows = result.fetchall()

        # Convert rows to list of dicts
        columns = result.keys()
        data = [dict(zip(columns, row)) for row in rows]

    return data


def part_distrubution_by_country(engine):

    query_text = """
    SELECT
      a."countryOfOrigin",
      COUNT(DISTINCT a."articleNo") AS parts_count
    FROM
      "articlevehiclelink" AS avl
    INNER JOIN "articles" AS a
      ON avl."articleNo" = a."articleNo"
      AND avl."supplierId" = a."supplierId"
    GROUP BY
      a."countryOfOrigin"
    ORDER BY
      parts_count DESC;
    """

    query = text(query_text)

    with Session(engine) as session:
        result = session.exec(query)
        rows = result.fetchall()

        # Convert rows to list of dicts
        columns = result.keys()
        data = [dict(zip(columns, row)) for row in rows]

    return data


def top_5_parts_by_price(engine):

    query_text = """
    SELECT
        p."productGroupId",
        p."description" AS "partDescription",
        c."description" AS "categoryDescription",
        ROUND(AVG(a."price")::numeric, 2) AS avg_price,
        COUNT(*) AS num_articles
    FROM
        "articlevehiclelink" AS avl
    INNER JOIN "articles" AS a
        ON avl."articleNo" = a."articleNo"
        AND avl."supplierId" = a."supplierId"
    INNER JOIN "parts" AS p
        ON avl."productGroupId" = p."productGroupId"
    INNER JOIN "category" AS c
        ON p."categoryId" = c."categoryId"
    GROUP BY
        p."productGroupId",
        p."description",
        c."description"
    ORDER BY
        avg_price DESC
    LIMIT 5;
    """

    query = text(query_text)

    with Session(engine) as session:
        result = session.exec(query)
        rows = result.fetchall()

        # Convert rows to list of dicts
        columns = result.keys()
        data = [dict(zip(columns, row)) for row in rows]

    return data


def vehicle_summary(engine):

    query_text = """
    SELECT
      m."description" AS manufacturer,
      mo."description" AS model,
      v."description" AS vehicle
    FROM
      "vehicle" v
    INNER JOIN "manufacturers" m
      ON v."manufacturerId" = m."manufacturerId"
    INNER JOIN "models" mo
      ON v."modelSeriesId" = mo."modelSeriesId"
    ORDER BY
      manufacturer,
      model,
      vehicle;
    """

    query = text(query_text)

    with Session(engine) as session:
        result = session.exec(query)
        rows = result.fetchall()

        # Convert rows to list of dicts
        columns = result.keys()
        data = [dict(zip(columns, row)) for row in rows]

    return data


def categories_modelled(engine, query_text=None):

    if query_text is None:
        # Default query matching your example
        query_text = """
        SELECT
          c."description" AS categoryDescription,
          COUNT(DISTINCT a."articleNo") AS num_articles
        FROM
          "articles" a
        INNER JOIN "articlevehiclelink" avl
          ON a."articleNo" = avl."articleNo"
          AND a."supplierId" = avl."supplierId"
        INNER JOIN "parts" p
          ON avl."productGroupId" = p."productGroupId"
        INNER JOIN "category" c
          ON p."categoryId" = c."categoryId"
        GROUP BY
          c."description"
        ORDER BY
          num_articles DESC;
        """

    query = text(query_text)

    with Session(engine) as session:
        result = session.exec(query)
        rows = result.fetchall()

        # Convert rows to list of dicts
        columns = result.keys()
        data = [dict(zip(columns, row)) for row in rows]

    return data


print(vehicle_summary(engine))