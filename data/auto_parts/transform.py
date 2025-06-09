def parse_categories(data):
    nodes, edges = [], []

    def traverse(category_dict, parent_id=None):
        for cat_id, cat_data in category_dict.items():
            nodes.append({'id': cat_id, 'text': cat_data['text']})
            if parent_id:
                edges.append({'from': parent_id, 'to': cat_id})
            if cat_data.get('children'):
                traverse(cat_data['children'], parent_id=cat_id)

    traverse(data['categories'])
    return nodes, edges

def transform_data_articles_list(data):
    articles_out = []
    suppliers_out = {}
    specs_out = []
    oems_out = []
    vehicles_out = []
    article_spec_rel = []
    article_oem_rel = []
    article_vehicle_rel = []

    for article in data['articles']:
        # Article
        articles_out.append({
            'articleId': article['articleId'],
            'articleNo': article['articleNo'],
            'productName': article['articleProductName'],
            'image': article.get('s3ImageLink', ''),
            'supplierId': article['supplierId']
        })

        # Supplier
        suppliers_out[article['supplierId']] = {
            'supplierId': article['supplierId'],
            'supplierName': article['supplierName']
        }

        # Specifications
        for spec in article.get('allSpecifications', []):
            spec_id = f"{article['articleId']}_{spec['criteriaName']}"
            specs_out.append({
                'specId': spec_id,
                'name': spec['criteriaName'],
                'value': spec['criteriaValue']
            })
            article_spec_rel.append({
                'articleId': article['articleId'],
                'specId': spec_id
            })

        # OEMs
        for oem in article.get('oemNo', []):
            oem_id = f"{oem['oemBrand']}_{oem['oemDisplayNo']}"
            oems_out.append({
                'oemId': oem_id,
                'brand': oem['oemBrand'],
                'displayNo': oem['oemDisplayNo']
            })
            article_oem_rel.append({
                'articleId': article['articleId'],
                'oemId': oem_id
            })

        # Vehicles
        for vehicle in article.get('compatibleCars', []):
            vehicles_out.append(vehicle)
            article_vehicle_rel.append({
                'articleId': article['articleId'],
                'vehicleId': vehicle['vehicleId']
            })

    # Deduplicate
    suppliers_out = list(suppliers_out.values())
    vehicles_out = list({v['vehicleId']: v for v in vehicles_out}.values())
    oems_out = list({o['oemId']: o for o in oems_out}.values())

    return {
        'articles': articles_out,
        'suppliers': suppliers_out,
        'specifications': specs_out,
        'oems': oems_out,
        'vehicles': vehicles_out,
        'article_spec_rel': article_spec_rel,
        'article_oem_rel': article_oem_rel,
        'article_vehicle_rel': article_vehicle_rel
    }