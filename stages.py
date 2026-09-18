import json
import os
import re
import xml.etree.ElementTree as ET


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NS = "mvz2:"
WIKI_JSON_TITLE = "Stages.json"

CHAPTER_NAMES = {
    1: "万圣夜", 2: "梦境世界", 3: "辉针城",
    4: "梦殿大祀庙", 5: "圣辇船", 6: "地灵殿",
}
EXTRA_CHAPTERS = {"序章": "序章"}
MODE_NAMES = {
    "minigame": "小游戏",
    "puzzle": "解密模式",
    "puzzle_endless": "解密模式",
    "endless": "无尽模式",
    "boss_endless": "无尽模式",
    "special": "特殊关卡",
}
MODE_ORDER = {
    "minigame": 9000, "puzzle": 9500, "puzzle_endless": 9500,
    "endless": 9800, "boss_endless": 9800, "special": 9900,
}
EXCLUDED_STAGE_IDS = {
    "debug", "i_zombie_debug",
    "halloween_endless", "dream_endless", "castle_endless",
    "mausoleum_endless", "ship_endless", "palace_endless",
    "InfinityFrankenstein", "InfinityNightmare", "InfinitySeija",
    "InfinityWither", "InfinityGiant", "InfinityRedDragon",
    "InfinityLockedChest", "SeijaRevenge", "heavy_weapon",
    "HeavyWeapon_Plus", "HeavyWeaponBossRush",
    "HeavyWeaponVSMannequin", "locked_chests_revenge", "PacZombie_2",
    "BalloonParty",
}
NAME_ALIASES = {"emperor": "皇帝僵尸"}
SPECIAL_NO_ICON_SPAWNS = {
    "undead_flying_object_blitz": "不死飞行物（特殊出怪）",
}
COLOR_RE = re.compile(r"</?color(?:=[^>]*)?>", re.I)
PAREN_RE = re.compile(r"[（(][^）)]*[）)]\s*$")


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
        if item_id and name:
            names[item_id] = name
            names[normalized_id(item_id)] = name
    return names


def stage_display_names(stages):
    world_numbers = {}
    names = {}
    for stage in stages:
        stage_id = stage.get("id", "")
        name = stage.get("name") or stage_id
        day_number = int_value(stage.get("dayNumber"))
        if day_number is None:
            names[stage_id] = name
        else:
            world_number = world_numbers.setdefault(name, len(world_numbers) + 1)
            names[stage_id] = f"关卡{world_number}-{day_number}"
    return names, world_numbers


def clean_wiki_name(value):
    value = COLOR_RE.sub("", value or "").strip()
    return PAREN_RE.sub("", value).strip()


def spawn_record(spawn, entity_names):
    entity = short(spawn.get("id", ""))
    if entity in SPECIAL_NO_ICON_SPAWNS:
        return {"id": entity, "name": SPECIAL_NO_ICON_SPAWNS[entity], "noIcon": True}
    return compact_dict({
        "id": entity,
        "name": entity_names.get(entity) or entity_names.get(normalized_id(entity))
        or NAME_ALIASES.get(entity) or entity,
    })


def stage_records(stages, entity_names, display_names):
    records = []
    for stage in stages:
        spawns = stage.find("spawns")
        records.append(compact_dict({
            "id": stage.get("id"),
            "name": stage.get("name"),
            "displayName": display_names.get(stage.get("id")),
            "type": stage.get("type"),
            "dayNumber": int_value(stage.get("dayNumber")),
            "spawns": [spawn_record(spawn, entity_names) for spawn in spawns.findall("spawn")]
            if spawns is not None else [],
        }))
    return records


def category_of(stage, world_numbers):
    name = stage.get("name") or ""
    if stage.get("dayNumber") not in (None, ""):
        number = world_numbers.get(name)
        return CHAPTER_NAMES.get(number, name), True, number or 8999
    if name in EXTRA_CHAPTERS:
        return EXTRA_CHAPTERS[name], True, 0
    stage_type = stage.get("type")
    if stage_type in MODE_NAMES:
        return MODE_NAMES[stage_type], False, MODE_ORDER[stage_type]
    return None, False, 9999


def stage_link(stage, display_names):
    stage_id = stage.get("id", "")
    if stage.get("dayNumber") not in (None, ""):
        return display_names.get(stage_id)
    return clean_wiki_name(stage.get("name") or display_names.get(stage_id) or stage_id)


def monster_name(entity_id, entity_names):
    return (
        entity_names.get(entity_id)
        or entity_names.get(entity_id.lower())
        or NAME_ALIASES.get(entity_id)
        or SPECIAL_NO_ICON_SPAWNS.get(entity_id)
        or entity_id
    )


def monster_records(stages, entity_names, display_names, world_numbers):
    positions = {stage.get("id"): index for index, stage in enumerate(stages)}
    index = {}
    for stage in stages:
        stage_id = stage.get("id")
        if stage_id in EXCLUDED_STAGE_IDS:
            continue
        spawns = stage.find("spawns")
        if spawns is None:
            continue
        category, is_chapter, order = category_of(stage, world_numbers)
        link = stage_link(stage, display_names)
        if category is None or not link:
            continue
        for spawn in spawns.findall("spawn"):
            entity_id = short((spawn.get("id") or "").strip())
            if not entity_id:
                continue
            groups = index.setdefault(entity_id, {})
            group = groups.setdefault(category, {
                "category": category,
                "chapter": is_chapter,
                "order": order,
                "stages": {},
            })
            group["stages"].setdefault(stage_id, {
                "link": link, "id": stage_id,
            })

    monsters = []
    for entity_id, groups in index.items():
        categories = []
        for group in sorted(groups.values(), key=lambda item: (item["order"], item["category"])):
            stage_list = sorted(
                group["stages"].values(),
                key=lambda item: positions.get(item["id"], 9999),
            )
            categories.append({
                "category": group["category"],
                "chapter": group["chapter"],
                "stages": [{"link": stage["link"]} for stage in stage_list],
            })
        name = monster_name(entity_id, entity_names)
        record = {"id": entity_id, "name": name}
        record["stageCount"] = sum(len(group["stages"]) for group in categories)
        record["stagesByCategory"] = categories
        monsters.append(record)
    monsters.sort(key=lambda item: (-item["stageCount"], item["name"]))
    return monsters


def convert():
    stages = parse_xml("stages.xml").findall("stage")
    entity_names = load_entity_names()
    display_names, world_numbers = stage_display_names(stages)
    return json.dumps({
        "entries": stage_records(stages, entity_names, display_names),
        "monsters": monster_records(stages, entity_names, display_names, world_numbers),
    }, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    print(convert())