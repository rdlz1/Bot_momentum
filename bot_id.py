import requests

BOT_TOKEN = '8054600297:AAFSCq0AcjoM9zr8z73Qx3yGs2jT-aKSNts'

response = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates')
data = response.json()

print(data)