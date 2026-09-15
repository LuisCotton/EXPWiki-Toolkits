"""反向索引：统计每个怪物在哪些关卡登场。

数据源与 stages.py 保持一致（stages.xml 里 <stage><spawns> 的自然出怪表），
但把「关卡 -> 怪物」翻转为「怪物 -> 关卡」，供怪物页面的「登场关卡」章节使用。

用法：
    py -3 stages_enemy.py                # 生成并上传 EnemyStages.json
    py -3 stages_enemy.py --no-upload    # 只打印，不上传
    py -3 "upload all.py"                # 连同其他转换脚本一起上传

配套的 wiki 端渲染模块是 stages_enemy.lua（上传为 Module:StagesEnemy）：
    {{#invoke:StagesEnemy|getEnemyStages|{{PAGENAME}}}}   单个怪物的登场关卡
    {{#invoke:StagesEnemy|getStages|怪物}}                 全怪物总表

注意：只统计关卡 XML 里 <spawns> 的自然出怪表。以下两类数据不在 XML 中，
本脚本无法生成，需要人工补充：
  * 旗帜事件等「特殊生成」的怪物（如旗帜僵尸）；
  * 解谜/教程关（这些关卡在 stages.xml 里没有 <spawns> 节点）。
"""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NS = "mvz2:"
WIKI_JSON_TITLE = "EnemyStages.json"

# 章节号 -> wiki 章节名。关卡号沿用 stages.py 的算法（按关卡在 XML 中的出现顺序编号），
# 映射写死在这里。注意：XML 里的章节名（万圣夜）和 wiki 上的章节名（永夜沼泽）并不一致。
CHAPTER_NAMES = {
    1: "永夜沼泽",
    2: "梦境世界",
    3: "辉针城",
    4: "梦殿大祀庙",
    5: "圣辇船",
    6: "地灵殿",
}

# 无 dayNumber 但有独立 wiki 页面的剧情关，单独成组。
EXTRA_CHAPTERS = {
    "序章": "序章",
}

# stage 的 type -> wiki 上的模式名。
MODE_NAMES = OrderedDict([
    ("minigame", "小游戏"),
    ("puzzle", "解密模式"),
    ("puzzle_endless", "解密模式"),
    ("endless", "无尽模式"),
    ("boss_endless", "无尽模式"),
    ("special", "特殊关卡"),
])

# 非章节分组在总排序里的位置（章节用关卡号 1-6 排序）。
MODE_ORDER = {
    "minigame": 9000,
    "puzzle": 9500,
    "puzzle_endless": 9500,
    "endless": 9800,
    "boss_endless": 9800,
    "special": 9900,
}

# 不参与统计的关卡。测试关卡没有 wiki 页面；下面这批关卡在游戏 XML 里存在，
# 但 wiki 上页面尚未创建，写进怪物页面只会得到红链，所以暂不收录。
# （已逐个用 api.php 核对过页面确实不存在；等对应页面建好后，从这里删掉即可。）
EXCLUDED_STAGE_IDS = {
    # 测试关卡
    "debug",
    "i_zombie_debug",
    # 无尽模式：6 个页面都还没建
    "halloween_endless",
    "dream_endless",
    "castle_endless",
    "mausoleum_endless",
    "ship_endless",
    "palace_endless",
    # 无限 Boss 系列
    "InfinityFrankenstein",
    "InfinityNightmare",
    "InfinitySeija",
    "InfinityWither",
    "InfinityGiant",
    "InfinityRedDragon",
    "InfinityLockedChest",
    # 其余尚未建页面的小游戏
    "SeijaRevenge",
    "heavy_weapon",
    "HeavyWeapon_Plus",
    "HeavyWeaponBossRush",
    "HeavyWeaponVSMannequin",
    "locked_chests_revenge",
    "PacZombie_2",
    "BalloonParty",
}

# entity id -> wiki 页面名。用于 XML 里查不到中文名、但 wiki 上确实有页面的怪物。
# 例：stages.xml 里 emperor 没有对应实体，但 wiki 上有「皇帝僵尸」页面。
NAME_ALIASES = {
    "emperor": "皇帝僵尸",
}

# stages.py 对这两个特殊出怪项的命名，保持一致，避免同一个怪出现两行。
SPECIAL_SPAWN_NAMES = {
    "undead_flying_object_blitz": "不死飞行物（特殊出怪）",
}

COLOR_RE = re.compile(r"</?color(?:=[^>]*)?>", re.I)
PAREN_RE = re.compile(r"[（(][^）)]*[）)]\s*$")


def short(value):
    return value[len(NS):] if isinstance(value, str) and value.startswith(NS) else value


def find_metas_dir():
    """定位 XML 目录：优先脚本同级，其次脚本上一级。

    其他工具脚本固定用 BASE_DIR/metas；这里多给一个回退，方便 metas 放在仓库上一级
    （例如 EXPWiki-Toolkits 与 metas 并列）时也能直接运行。两处都没有则返回脚本同级，
    并由 parse_xml 抛出「找不到文件」，便于排查。
    """
    beside = os.path.join(BASE_DIR, "metas")
    if os.path.isdir(beside):
        return beside
    parent = os.path.join(os.path.dirname(BASE_DIR), "metas")
    if os.path.isdir(parent):
        return parent
    return beside


METAS_DIR = find_metas_dir()


def parse_xml(name):
    with open(os.path.join(METAS_DIR, name), encoding="utf-8-sig") as source:
        return ET.fromstring(source.read())


def load_entity_names():
    """entity id -> 中文名。同时登记小写别名，避免大小写差异导致漏配。"""
    path = os.path.join(METAS_DIR, "entities.xml")
    if not os.path.exists(path):
        return {}
    names = {}
    for entry in parse_xml("entities.xml").findall(".//*[@id]"):
        entity_id = short(entry.get("id", ""))
        name = entry.get("name")
        if not entity_id or not name:
            continue
        names.setdefault(entity_id, name)
        names.setdefault(entity_id.lower(), name)
    return names


def clean_name(value):
    """去掉游戏内的颜色标记，以及名称末尾的消歧义括号（wiki 页面标题不带括号）。"""
    if not value:
        return ""
    text = COLOR_RE.sub("", value).strip()
    return PAREN_RE.sub("", text).strip() or text


def stage_type(stage):
    return (stage.get("type") or "").strip()


def int_value(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def build_display_names(stages):
    """复刻 stages.py 的 displayName 算法：章节按首次出现顺序编号，输出「关卡N-M」。

    stages.xml 里并没有 displayName，它只存在于 stages.py 生成的 Stages.json 中，
    所以这里必须用同样的规则重算一遍，否则关卡号会对不上 wiki 页面名。
    """
    world_numbers = {}
    display_names = {}
    for stage in stages:
        stage_id = stage.get("id")
        name = stage.get("name") or stage_id or ""
        day_number = int_value(stage.get("dayNumber"))
        if day_number is None:
            # 非章节关卡直接用关卡名，去掉游戏内的颜色标记。
            display_names[stage_id] = clean_name(name)
            continue
        world_number = world_numbers.setdefault(name, len(world_numbers) + 1)
        display_names[stage_id] = f"关卡{world_number}-{day_number}"
    return display_names


def stage_link(stage, display_names):
    """关卡在 wiki 上的链接目标 / 显示名。"""
    return display_names.get(stage.get("id")) or clean_name(stage.get("name") or stage.get("id") or "")


def chapter_number(stage, display_names):
    match = re.match(r"^关卡(\d+)-", display_names.get(stage.get("id")) or "")
    return int(match.group(1)) if match else None


def category_of(stage, display_names):
    """返回 (分组名, 是否章节分组, 排序键)。分不出组时返回 None。"""
    name = stage.get("name") or ""
    if name in EXTRA_CHAPTERS:
        return EXTRA_CHAPTERS[name], True, 0
    number = chapter_number(stage, display_names)
    if number in CHAPTER_NAMES:
        return CHAPTER_NAMES[number], True, number
    kind = stage_type(stage)
    mode = MODE_NAMES.get(kind)
    if mode:
        return mode, False, MODE_ORDER.get(kind, 9900)
    return None, False, 0


def monster_name(entity_id, entity_names):
    """按 中文名 -> wiki 别名 -> 特殊出怪命名 -> id 的顺序解析怪物显示名。"""
    return (
        entity_names.get(entity_id)
        or entity_names.get(entity_id.lower())
        or NAME_ALIASES.get(entity_id)
        or SPECIAL_SPAWN_NAMES.get(entity_id)
        or entity_id
    )


def convert():
    entity_names = load_entity_names()
    stages = parse_xml("stages.xml").findall("stage")
    display_names = build_display_names(stages)

    # 关卡在 XML 中的原始位置，用作最终排序依据，最贴近游戏内的关卡排列。
    position = {stage.get("id"): index for index, stage in enumerate(stages)}

    # 怪物 -> 分组名 -> {分组信息 + 关卡表}
    index = {}
    for stage in stages:
        stage_id = stage.get("id")
        if stage_id in EXCLUDED_STAGE_IDS:
            continue
        spawns = stage.find("spawns")
        if spawns is None:
            continue

        category, is_chapter, order = category_of(stage, display_names)
        link = stage_link(stage, display_names)
        if category is None or not link:
            continue

        for spawn in spawns.findall("spawn"):
            entity_id = short((spawn.get("id") or "").strip())
            if not entity_id:
                continue
            groups = index.setdefault(entity_id, {})
            group = groups.get(category)
            if group is None:
                group = groups[category] = {
                    "category": category,
                    "chapter": is_chapter,
                    "order": order,
                    "stages": {},
                }
            group["stages"].setdefault(stage_id, {
                "name": link,
                "link": link,
                "id": stage_id,
            })

    monsters = []
    for entity_id, groups in index.items():
        ordered = sorted(groups.values(), key=lambda group: (group["order"], group["category"]))
        stages_by_category = []
        for group in ordered:
            stage_list = sorted(group["stages"].values(), key=lambda item: position.get(item["id"], 9999))
            stages_by_category.append(OrderedDict([
                ("category", group["category"]),
                ("chapter", group["chapter"]),
                ("stages", stage_list),
            ]))

        record = OrderedDict([("id", entity_id), ("name", monster_name(entity_id, entity_names))])
        if record["name"] == entity_id:
            # 没有中文名，wiki 上会直接显示 id，方便事后人工修。
            record["needsName"] = True
        record["stageCount"] = sum(len(group["stages"]) for group in stages_by_category)
        record["stagesByCategory"] = stages_by_category
        monsters.append(record)

    # 登场数多的排前面，其次按名字。
    monsters.sort(key=lambda item: (-item["stageCount"], item["name"]))

    return json.dumps(
        {"source": "stages.xml", "monsters": monsters},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def main(upload=True):
    try:
        text = convert()
    except Exception as error:
        print(f"生成失败：{error}")
        return False

    if not upload:
        print(text)
        return True

    try:
        import login
        login.upload_text(WIKI_JSON_TITLE, text, "via stages_enemy.py")
        print(f"上传成功：{WIKI_JSON_TITLE}")
        return True
    except Exception as error:
        print(f"上传失败：{error}")
        return False


if __name__ == "__main__":
    main(upload="--no-upload" not in sys.argv)
