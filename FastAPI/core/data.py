from FastAPI.data.auto_parts.tecdoc import fetch_categories_data
import pandas as pd

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

def flatten_leaf_categories(categories, parent_id=None):
    rows = []
    for cat_id, cata_data in categories.items():
        if not cata_data['children']:
            rows.append({
                'id': cat_id,
                'text': cata_data['text'],
                'parent_id': parent_id
            })
        else:
            rows.extend(flatten_leaf_categories(cata_data['children'], parent_id=cat_id))
    return rows

def automotive_parts():
    parts = fetch_categories_data(vehicleId, manufacturerId)
    print(parts)

    rows = flatten_leaf_categories(parts['categories'])
    df = pd.DataFrame(rows)
    print(df)


if __name__ == "__main__":
    automotive_parts()