import json
import os
import xml.etree.ElementTree as ET


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WIKI_JSON_TITLE = "Module:Curses.json"


def clean_text(value):
    return (value or "").strip()


def read_xml_text(path):
    data = open(path, "rb").read()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")


def convert_data():
    xml_text = read_xml_text(os.path.join(BASE_DIR, "metas", "curses.xml"))
    root = ET.fromstring(xml_text)
    curses = []

    for curse in root.findall("curse"):
        texts = curse.find("texts")
        if texts is None:
            continue

        name = clean_text(texts.get("name"))
        effect = clean_text(texts.get("tooltip"))
        if not name and not effect:
            continue

        curses.append({
            "name": name,
            "effect": effect,
        })

    return curses


def convert():
    return json.dumps(convert_data(), ensure_ascii=False, separators=(",", ":"))