import json
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
METAS_DIR = os.path.join(BASE_DIR, "metas")
TALKS_DIR = os.path.join(METAS_DIR, "talks")
CHARACTERS_PATH = os.path.join(METAS_DIR, "talkcharacters.xml")
MUSICS_PATH = os.path.join(METAS_DIR, "musics.xml")
NS = "mvz2:"
WIKI_JSON_TITLE = "Talk.json"

CHAPTERS = {
    "prologue": "序章",
    "halloween": "万圣夜",
    "dream": "梦境世界",
    "castle": "辉针城",
    "mausoleum": "梦殿大祀庙",
    "ship": "圣辇船",
    "palace": "地灵殿",
}


def short(value):
    if isinstance(value, str) and value.startswith(NS):
        return value[len(NS):]
    return value


def compact_dict(values):
    return {
        key: value
        for key, value in values.items()
        if value not in (None, "", {}, [])
    }


def read_xml(path):
    with open(path, encoding="utf-8-sig") as source:
        return ET.fromstring(source.read())


def load_character_names():
    root = read_xml(CHARACTERS_PATH)
    names = {}
    for character in root.findall("character"):
        character_id = short(character.get("id", "").strip())
        name = character.get("name", "").strip()
        if character_id and name:
            names[character_id] = name
    return names


def load_music_names():
    root = read_xml(MUSICS_PATH)
    names = {}
    for music in root.findall("music"):
        name = music.get("name", "").strip()
        if not name:
            continue

        music_id = short(music.get("id", "").strip())
        if music_id:
            names[music_id] = name

        track = music.find("track")
        if track is not None:
            for track_id in track.attrib.values():
                track_id = short(track_id.strip())
                if track_id:
                    names[track_id] = name
    return names


def clean_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def sentence_text(sentence):
    text = sentence.find("text")
    return clean_text("".join(text.itertext())) if text is not None else ""


def script_sides(root):
    sides = defaultdict(Counter)
    for character in root.findall(".//characters/character"):
        character_id = short(character.get("id", ""))
        side = character.get("side")
        if character_id and side:
            sides[character_id][side] += 1

    pattern = re.compile(r"^character\s+create\s+(\S+)\s+(left|right|self)(?:\s|$)")
    for script in root.findall(".//script"):
        match = pattern.match(clean_text(script.text))
        if match:
            sides[short(match.group(1))][match.group(2)] += 1
    return sides


def preferred_sides(roots):
    totals = defaultdict(Counter)
    for root in roots:
        for character_id, counts in script_sides(root).items():
            totals[character_id].update(counts)
    return {
        character_id: counts.most_common(1)[0][0]
        for character_id, counts in totals.items()
    }


def style_for(side):
    return {"left": 1, "right": 2, "self": 3}.get(side, 1)


def parse_section(section, names, defaults):
    local_sides = {}
    characters = []
    for character in section.findall("./characters/character"):
        character_id = short(character.get("id", ""))
        side = character.get("side") or defaults.get(character_id, "left")
        local_sides[character_id] = side
        characters.append(compact_dict({
            "id": character_id,
            "name": names.get(character_id, character_id),
            "side": side,
            "variant": short(character.get("variant")),
        }))

    sentences = []
    for sentence in section.findall("./sentences/sentence"):
        speaker_id = short(sentence.get("speaker", ""))
        side = local_sides.get(speaker_id) or defaults.get(speaker_id, "left")
        sentences.append(compact_dict({
            "speaker": speaker_id,
            "name": names.get(speaker_id, speaker_id or "？？？"),
            "side": side,
            "style": style_for(side),
            "text": sentence_text(sentence),
            "description": clean_text(sentence.get("description")),
            "variant": short(sentence.get("variant")),
        }))

    section_name = section.findtext("text")
    return compact_dict({
        "name": clean_text(section_name),
        "characters": characters,
        "sentences": sentences,
    })


def parse_chapter(key, root, names, music_names, defaults):
    groups = []
    for group in root.findall("group"):
        archive = group.find("archive")
        group_name = archive.get("name", "") if archive is not None else group.get("id", "")
        music_id = short(archive.get("music")) if archive is not None else None
        groups.append(compact_dict({
            "id": group.get("id"),
            "name": group_name,
            "tags": [short(tag.strip()) for tag in group.get("tags", "").split(";") if tag.strip()],
            "music": music_names.get(music_id, music_id),
            "sections": [
                parse_section(section, names, defaults)
                for section in group.findall("section")
            ],
        }))

    try:
        order = int(root.get("order", "0"))
    except ValueError:
        order = root.get("order", "0")
    return {
        "key": key,
        "name": CHAPTERS[key],
        "file": key + ".xml",
        "order": order,
        "groups": groups,
    }


def convert():
    names = load_character_names()
    music_names = load_music_names()
    roots = {}
    for key in CHAPTERS:
        path = os.path.join(TALKS_DIR, key + ".xml")
        if not os.path.exists(path):
            raise FileNotFoundError("缺少剧情 XML：" + path)
        roots[key] = read_xml(path)

    defaults = preferred_sides(roots.values())
    chapters = [
        parse_chapter(key, root, names, music_names, defaults)
        for key, root in roots.items()
    ]
    chapters.sort(key=lambda chapter: chapter["order"])
    return json.dumps(
        {"chapters": chapters},
        ensure_ascii=False,
        separators=(",", ":"),
    )


if __name__ == "__main__":
    print(convert())