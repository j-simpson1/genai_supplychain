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