import json
import os
import xml.etree.ElementTree as ET


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NS = "mvz2:"
WIKI_JSON_TITLE = "DeathMessage.json"


def short(value):
    return value[len(NS):] if isinstance(value, str) and value.startswith(NS) else value


def convert_data():
    source_path = os.path.join(BASE_DIR, "metas", "entities.xml")
    root = ET.parse(source_path).getroot()
    section = root.find("entries")
    result = []

    for entry in (list(section) if section is not None else []):
        message = entry.get("deathMessage")
        if message is None:
            continue

        entity_id = short(entry.get("id", "").strip())
        name = entry.get("name", "").strip()
        message = message.strip()
        if not entity_id or not name or not message:
            continue

        result.append({
            "id": entity_id,
            "name": name,
            "deathMessage": message,
        })

    return result


def convert():
    return json.dumps(convert_data(), ensure_ascii=False, separators=(",", ":"))