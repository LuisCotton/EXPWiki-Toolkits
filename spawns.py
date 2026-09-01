import json
import os
import xml.etree.ElementTree as ET


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NS = "mvz2:"
WIKI_JSON_TITLE = "Spawns.json"


def short(value):
    return value[len(NS):] if isinstance(value, str) and value.startswith(NS) else value


def bool_value(value):
    return str(value).lower() == "true"


def int_value(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def compact_dict(values):
    return {key: value for key, value in values.items() if value not in (None, "", {}, [])}


def child_attrs(entry, name):
    child = entry.find(name)
    return dict(child.attrib) if child is not None else {}


def parse_xml(name):
    with open(os.path.join(BASE_DIR, "metas", name), encoding="utf-8-sig") as source:
        return ET.fromstring(source.read())


def normalized_id(value):
    return short(str(value or "").strip()).lower()


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


def entity_id(entry):
    entity = entry.find("entity")
    return short((entity.get("id") if entity is not None else None) or entry.get("entity") or "")


def entity_extra(entry):
    entity = entry.find("entity")
    if entity is None:
        return {}
    return {key: int_value(value) for key, value in entity.attrib.items() if key != "id"}


def convert():
    source_path = os.path.join(BASE_DIR, "metas", "spawns.xml")
    root = ET.parse(source_path).getroot()
    entity_names = load_entity_names()
    entries = []

    for entry in root.findall("entry"):
        spawn = child_attrs(entry, "spawn")
        preview = child_attrs(entry, "preview")
        terrain = child_attrs(entry, "terrain")
        weight = child_attrs(entry, "weight")
        eid = entity_id(entry)
        record = compact_dict({
            "id": entry.get("id"),
            "entity": eid,
            "name": (
                entity_names.get(eid)
                or entity_names.get(normalized_id(eid))
                or entry.get("id")
            ),
            "type": entry.get("type"),
            "noEndless": bool_value(entry.get("noEndless")) or None,
            "entityArgs": entity_extra(entry),
            "level": int_value(spawn.get("level")),
            "minWave": int_value(spawn.get("minWave")),
            "preview": compact_dict({
                "count": int_value(preview.get("count")),
                "variant": int_value(preview.get("variant")),
            }),
            "terrain": compact_dict({
                "water": bool_value(terrain.get("water")) or None,
                "air": bool_value(terrain.get("air")) or None,
                "excludedTags": short(terrain.get("excludedTags")) if terrain.get("excludedTags") else None,
            }),
            "weight": compact_dict({
                "base": int_value(weight.get("base")),
                "decreaseStart": int_value(weight.get("decreaseStart")),
                "decreaseEnd": int_value(weight.get("decreaseEnd")),
                "decreasePerFlag": int_value(weight.get("decreasePerFlag")),
            }),
        })
        entries.append(record)

    return json.dumps(entries, ensure_ascii=False, separators=(",", ":"))

