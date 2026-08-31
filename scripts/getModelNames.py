import requests
from pathlib import Path
import json

config_path = Path(__file__).resolve().parent.parent / "config.json"
with config_path.open(encoding="utf-8") as file:
    config = json.load(file)

models = requests.get(config["llama"]["models_url"]).json()

print(models)
