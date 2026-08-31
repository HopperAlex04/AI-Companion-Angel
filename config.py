from pathlib import Path
import json
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as file:
        return json.load(file)


config = load_config()
