import requests
from auth import get_access_token  # assuming you put it in a separate file

access_token = get_access_token()

endpoint = 'https://api.powerbi.com/v1.0/myorg/groups'
headers = {
    'Authorization': f'Bearer {access_token}'
}

response = requests.get(endpoint, headers=headers)
if response.status_code == 200:
    for group in response.json().get('value', []):
        print(f"{group['name']} (ID: {group['id']})")
else:
    print(f"API call failed: {response.status_code}")
    print(response.text)