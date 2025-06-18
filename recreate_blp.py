import requests

response = requests.post(
    "https://onpointparlays-web.onrender.com/drop-and-recreate-blp",
    headers={"X-Admin-Secret": "letmein"}
)

print(response.text)
