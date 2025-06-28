import pandas as pd
from FastAPI.data.auto_parts.tecdoc import fetch_categories_data, get_article_list
from sqlmodel import Session, select
from sqlalchemy import text

from FastAPI.database.models import Manufacturers, Vehicle
from FastAPI.database.database import engine
from FastAPI.database.models import Manufacturers, Models, Vehicle, Parts

# Example TOYOTA RAV 4 V
langId = "4" # English (GB)
manufacturerId = "111" # TOYOTA
modelSeriesId = "39268" # RAV 4 V (_A5_, _H5_)
typeId = "1" # Automobile
countryFilterId = "91" # Great Britain
vehicleId = "140099" # 2.5 Hybrid AWD (AXAH54)
productGroupId = "100030" # Brake Pad
articleNumber = "0 986 495 169" # Bosch
articleId = "71734"
supplierId = "30" # Bosch

def upload_parts_to_db(parts_df):
    with Session(engine) as session:
        for _, row in parts_df.iterrows():
            part = Parts(
                productGroupId=int(row['productGroupId']),
                Description=row['description'],
                manufacturerId=int(111),
                vehicleId=int(140099)
            )
            session.add(part)
        session.commit()


def flatten_leaf_categories(categories, parent_id=None):
    rows = []
    for cat_id, cata_data in categories.items():
        if not cata_data['children']:
            rows.append({
                'productGroupId': cat_id,
                'description': cata_data['text']
            })
        else:
            rows.extend(flatten_leaf_categories(cata_data['children'], parent_id=cat_id))
    return rows

def clear_database():
    with Session(engine) as session:
        session.exec(text("TRUNCATE TABLE articlevehiclelink, parts, vehicle, models, manufacturers, articles, suppliers RESTART IDENTITY CASCADE;"))
        session.commit()

def automotive_parts():
    parts = fetch_categories_data(vehicleId, manufacturerId)
    print(parts)

    parts_dict_list = flatten_leaf_categories(parts['categories'])
    parts_df = pd.DataFrame(parts_dict_list)
    print(parts_df)

    clear_database()

    with Session(engine) as session:
        manufacturer = Manufacturers(manufacturerId=111, description="TOYOTA")
        session.add(manufacturer)

        model = Models(
            modelSeriesId=39268,
            description="RAV 4 V (_A5_, _H5_)",
            manufacturerId=111
        )
        session.add(model)

        vehicle = Vehicle(
            vehicleId=140099,
            description="2.5 Hybrid AWD (AXAH54)",
            manufacturerId=111,
            modelSeriesId=39268
        )
        session.add(vehicle)

        session.commit()

    upload_parts_to_db(parts_df)

    print(get_article_list(manufacturerId, vehicleId, productGroupId))


if __name__ == "__main__":
    automotive_parts()