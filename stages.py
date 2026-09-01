import json
import os
import xml.etree.ElementTree as ET


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NS = "mvz2:"
WIKI_JSON_TITLE = "Stages.json"
SPECIAL_NO_ICON_SPAWNS = {
    "undead_flying_object_blitz": "不死飞行物（特殊出怪）",
}


def short(value):
    return value[len(NS):] if isinstance(value, str) and value.startswith(NS) else value


def int_value(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def compact_dict(values):
    return {key: value for key, value in values.items() if value not in (None, "", {}, [])}


def normalized_id(value):
    return short(str(value or "").strip()).lower()


def parse_xml(path):
    with open(os.path.join(BASE_DIR, "metas", path), encoding="utf-8-sig") as source:
        return ET.fromstring(source.read())


def load_entity_names():
    path = os.path.join(BASE_DIR, "metas", "entities.xml")
    if not os.path.exists(path):
        return {}
    root = parse_xml("entities.xml")
    section = root.find("entries")
    names = {}
    for entry in (list(section) if section is not None else []):
        item_id = short(entry.get("id", ""))
        name = entry.get("name")
        if not item_id or not name:
            continue
        names[item_id] = name
        names[normalized_id(item_id)] = name
    return names


def stage_display_name(stage, world_numbers):
    name = stage.get("name") or stage.get("id") or ""
    day_number = int_value(stage.get("dayNumber"))
    if day_number is None:
        return name

    world_number = world_numbers.setdefault(name, len(world_numbers) + 1)
    return f"关卡{world_number}-{day_number}"


def spawn_record(spawn, entity_names):
    entity = short(spawn.get("id", ""))
    if entity in SPECIAL_NO_ICON_SPAWNS:
        return compact_dict({
            "id": entity,
            "name": SPECIAL_NO_ICON_SPAWNS[entity],
            "noIcon": True,
        })
    return compact_dict({
        "id": entity,
        "name": entity_names.get(entity) or entity_names.get(normalized_id(entity)) or entity,
    })


def convert():
    root = parse_xml("stages.xml")
    entity_names = load_entity_names()
    world_numbers = {}
    entries = []

    for stage in root.findall("stage"):
        spawns = stage.find("spawns")
        spawn_list = [spawn_record(spawn, entity_names) for spawn in spawns.findall("spawn")] if spawns is not None else []
        record = compact_dict({
            "id": stage.get("id"),
            "name": stage.get("name"),
            "displayName": stage_display_name(stage, world_numbers),
            "type": stage.get("type"),
            "dayNumber": int_value(stage.get("dayNumber")),
            "spawns": spawn_list,
        })
        entries.append(record)

    return json.dumps(entries, ensure_ascii=False, separators=(",", ":"))

