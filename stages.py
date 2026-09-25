import json
import os
import re
import xml.etree.ElementTree as ET


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NS = "mvz2:"
WIKI_JSON_TITLE = "Stages.json"

CHAPTER_NAMES = {
    1: "永夜沼泽", 2: "梦境世界", 3: "辉针城",
    4: "梦殿大祀庙", 5: "圣辇船", 6: "地灵殿",
}
WORLD_CHAPTERS = {
    "万圣夜": "永夜沼泽",
    "梦境世界": "梦境世界",
    "辉针城": "辉针城",
    "梦殿大祀庙": "梦殿大祀庙",
    "圣辇船": "圣辇船",
    "地灵殿": "地灵殿",
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
    name = stage.get("name", "")
    if stage.get("dayNumber") is not None:
        number = world_numbers.get(name, 8999)
        return WORLD_CHAPTERS.get(name, CHAPTER_NAMES.get(number, name)), number
    if name in EXTRA_CHAPTERS:
        return EXTRA_CHAPTERS[name], 0
    stage_type = stage.get("type")
    if stage_type in MODE_NAMES:
        return MODE_NAMES[stage_type], MODE_ORDER[stage_type]
    return None, 9999


def stage_link(stage):
    if stage.get("dayNumber") is not None:
        return stage.get("displayName")
    return clean_wiki_name(stage.get("name") or stage.get("displayName") or stage.get("id", ""))


def monster_records(stages, world_numbers):
    index = {}
    for position, stage in enumerate(stages):
        stage_id = stage.get("id")
        if stage_id in EXCLUDED_STAGE_IDS:
            continue
        category, order = category_of(stage, world_numbers)
        link = stage_link(stage)
        if category is None or not link:
            continue
        for spawn in stage.get("spawns", []):
            entity_id = spawn.get("id", "")
            if not entity_id:
                continue
            name = spawn.get("name") or entity_id
            monster = index.setdefault(name, {
                "name": name,
                "ids": set(),
                "groups": {},
            })
            monster["ids"].add(entity_id)
            groups = monster["groups"]
            group = groups.setdefault(category, {
                "category": category,
                "order": order,
                "stages": {},
            })
            group["stages"].setdefault(stage_id, {
                "link": link,
                "position": position,
            })

    monsters = []
    for monster in index.values():
        categories = []
        for group in sorted(monster["groups"].values(), key=lambda item: (item["order"], item["category"])):
            stage_list = sorted(
                group["stages"].values(),
                key=lambda item: item["position"],
            )
            categories.append({
                "category": group["category"],
                "stages": [{"link": stage["link"]} for stage in stage_list],
            })
        record = {"ids": sorted(monster["ids"]), "name": monster["name"]}
        record["stageCount"] = sum(len(group["stages"]) for group in categories)
        record["stagesByCategory"] = categories
        monsters.append(record)
    monsters.sort(key=lambda item: (-item["stageCount"], item["name"]))
    return monsters


def convert():
    stages = parse_xml("stages.xml").findall("stage")
    entity_names = load_entity_names()
    display_names, world_numbers = stage_display_names(stages)
    entries = stage_records(stages, entity_names, display_names)
    return json.dumps({
        "entries": entries,
        "monsters": monster_records(entries, world_numbers),
    }, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    print(convert())