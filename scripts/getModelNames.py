import requests

models = requests.get(
    "http://0.0.0.0:8080/v1/models"
).json()

print(models)
