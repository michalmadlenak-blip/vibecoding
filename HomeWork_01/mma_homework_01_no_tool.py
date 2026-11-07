import requests
import os
from pprint import pprint
from dotenv import load_dotenv
load_dotenv()

openai_api_key = os.environ.get("OPENAI_API_KEY")
openai_api_url = os.environ.get("OPENAI_API_URL")
openai_model = os.environ.get("OPENAI_MODEL")
openai_system_role = os.environ.get("OPENAI_SYSTEM_ROLE")

# Header
headers = {
    "Content-Type": "application/json", 
    "Authorization": f"Bearer {openai_api_key}"
}

# Body
data = {
    "model": openai_model,
    "messages": [
        {"role": "system", "content": openai_system_role},
        {"role": "user", "content": "Calculate 836 * 85, give just the output, US Format"},
    ],
}

# Request
response = requests.post(
    openai_api_url, headers=headers, json=data
)

print("--- Full response: ---")
pprint(response.json())
print("--- Response text: ---")
print(response.json()["choices"][0]["message"]["content"])
