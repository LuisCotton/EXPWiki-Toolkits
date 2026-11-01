import json
import os
import xml.etree.ElementTree as ET


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WIKI_JSON_TITLE = "Module:Musics.json"


def clean_text(value):
    return " ".join((value or "").split())


def description_text(music):
    description = music.find("description")
    if description is None:
        return ""

    paragraphs = []
    for paragraph in description.findall("p"):
        paragraphs.append(clean_text("".join(paragraph.itertext())))
    return "<br>".join(paragraphs)


def convert_data():
    root = ET.parse(os.path.join(BASE_DIR, "metas", "musics.xml")).getroot()
    musics = []

    for music in root.findall("music"):
        music_id = clean_text(music.get("id"))
        name = clean_text(music.get("name"))
        description = description_text(music)
        if not music_id and not name:
            continue

        musics.append({
            "id": music_id,
            "name": name,
            "description": description,
        })

    return musics


def convert():
    return json.dumps(convert_data(), ensure_ascii=False, separators=(",", ":"))