import requests
import os
from dotenv import load_dotenv

url = "https://tecdoc-catalog.p.rapidapi.com/languages/list"

load_dotenv()
headers = {
	"x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
	"x-rapidapi-host": "tecdoc-catalog.p.rapidapi.com"
}



response = requests.get(url, headers=headers)

print(response.json())