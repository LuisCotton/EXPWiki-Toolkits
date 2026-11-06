import json
import sys
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SPRITES_DIR = BASE_DIR / "sprites"
WIKI_JSON_TITLE = "Module:Sprites.json"
IMAGE_EXTENSIONS = {".png", ".jpg"}


def sort_key(path):
    return path.name.casefold()


def image_files():
    return [
        path for path in SPRITES_DIR.rglob("*")
        if path.is_file() and path.suffix.casefold() in IMAGE_EXTENSIONS
    ]


def wiki_file_names(files):
    by_stem = defaultdict(list)
    for path in files:
        by_stem[path.stem.casefold()].append(path)

    names = {}
    for duplicates in by_stem.values():
        if len(duplicates) == 1:
            path = duplicates[0]
            names[path] = path.name
            continue

        unresolved = list(duplicates)
        depth = 1
        while unresolved:
            candidates = defaultdict(list)
            for path in unresolved:
                relative_parts = path.parent.relative_to(SPRITES_DIR).parts
                suffix = " ".join(relative_parts[-depth:])
                candidate = f"{path.stem} ({suffix}){path.suffix}"
                candidates[candidate.casefold()].append((path, candidate))

            next_unresolved = []
            for matches in candidates.values():
                if len(matches) == 1:
                    path, candidate = matches[0]
                    names[path] = candidate
                else:
                    next_unresolved.extend(path for path, _ in matches)
            unresolved = next_unresolved
            depth += 1

    return names


def read_directory(directory, root, names):
    children = sorted(
        (path for path in directory.iterdir() if path.is_dir()),
        key=sort_key,
    )
    files = sorted(
        (
            {
                "name": path.name,
                "wikiName": names[path],
            }
            for path in directory.iterdir()
            if path.is_file() and path.suffix.casefold() in IMAGE_EXTENSIONS
        ),
        key=lambda item: item["name"].casefold(),
    )
    return {
        "path": directory.relative_to(root).as_posix(),
        "files": files,
        "children": [read_directory(child, root, names) for child in children],
    }


def convert_data():
    if not SPRITES_DIR.is_dir():
        raise FileNotFoundError(f"找不到 sprites 目录：{SPRITES_DIR}")
    names = wiki_file_names(image_files())
    return {
        "directories": [
            read_directory(directory, SPRITES_DIR, names)
            for directory in sorted(
                (path for path in SPRITES_DIR.iterdir() if path.is_dir()),
                key=sort_key,
            )
        ],
    }


def convert():
    return json.dumps(convert_data(), ensure_ascii=False, separators=(",", ":"))


def file_description(path):
    category = "sprites\\" + "\\".join(path.parent.relative_to(SPRITES_DIR).parts)
    return "== Licensing ==\n{{License|game}}\n\n[[Category:" + category + "]]"


def upload_entries():
    files = image_files()
    names = wiki_file_names(files)
    return [
        {
            "path": path,
            "wikiName": names[path],
            "text": file_description(path),
        }
        for path in sorted(files, key=lambda item: item.as_posix().casefold())
    ]


def revision_content(page):
    revisions = page.get("revisions") or []
    if not revisions:
        return ""
    return ((revisions[0].get("slots") or {}).get("main") or {}).get("content", "")


def existing_file_pages(api, names, batch_size=50):
    existing = {}
    names = list(names)
    for start in range(0, len(names), batch_size):
        batch = names[start:start + batch_size]
        result = api.request({
            "action": "query",
            "titles": "|".join("File:" + name for name in batch),
            "prop": "revisions",
            "rvslots": "main",
            "rvprop": "content",
        })
        normalized = {
            item.get("to", "").casefold(): item.get("from", "")
            for item in result.get("query", {}).get("normalized", [])
        }
        for page in result.get("query", {}).get("pages", []):
            if "missing" not in page:
                title = page.get("title", "")
                original = normalized.get(title.casefold(), title)
                existing[original.split(":", 1)[-1].casefold()] = {
                    "title": title,
                    "content": revision_content(page),
                }
    return existing


def ensure_file_page(api, filename, expected_text, current_text=None):
    title = filename if filename.lower().startswith("file:") else "File:" + filename
    if current_text is None:
        result = api.request({
            "action": "query",
            "titles": title,
            "prop": "revisions",
            "rvslots": "main",
            "rvprop": "content",
        })
        pages = result.get("query", {}).get("pages", [])
        current_text = revision_content(pages[0]) if pages and "missing" not in pages[0] else None
    if current_text != expected_text:
        api.upload_text(title, expected_text, "添加分类")
        return True
    return False


def upload_warnings(result):
    warnings = result.get("upload", {}).get("warnings", {})
    return warnings if isinstance(warnings, dict) else {}


def warning_text(warnings):
    parts = []
    for key, value in warnings.items():
        parts.append(str(key))
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        else:
            parts.append(str(value))
    return " ".join(parts)


def duplicate_filename(warnings):
    for key, value in warnings.items():
        if "duplicate" not in str(key).lower():
            continue
        values = value if isinstance(value, list) else [value]
        for item in values:
            if isinstance(item, str) and item:
                return item.split(":", 1)[-1]
    return None


def upload_sprites(api=None):
    if api is None:
        import login
        api = login.en_api

    entries = upload_entries()
    existing = existing_file_pages(api, (entry["wikiName"] for entry in entries))
    uploaded = 0
    skipped = 0
    updated = 0
    failed = []
    duplicates = []

    for index, entry in enumerate(entries, 1):
        wiki_name = entry["wikiName"]
        existing_page = existing.get(wiki_name.casefold())
        if existing_page:
            if ensure_file_page(api, existing_page["title"], entry["text"], existing_page["content"]):
                updated += 1
                print(f"({index}/{len(entries)}) 已存在并修正页面：{wiki_name}")
            else:
                print(f"({index}/{len(entries)}) 已存在且页面正确：{wiki_name}")
            skipped += 1
            continue

        try:
            with entry["path"].open("rb") as file_obj:
                result = api.upload_file(
                    wiki_name,
                    file_obj,
                    entry["text"],
                    "批量上传贴图",
                )
                warnings = upload_warnings(result)
                duplicate = duplicate_filename(warnings)
                if duplicate:
                    if ensure_file_page(api, duplicate, entry["text"]):
                        updated += 1
                    duplicates.append((duplicate, wiki_name))
                    skipped += 1
                    print(f"({index}/{len(entries)}) 内容重复，跳过上传：{wiki_name} -> {duplicate}")
                    continue
                warning_message = warning_text(warnings).lower()
                if "was-deleted" in warning_message or "was deleted" in warning_message:
                    file_obj.seek(0)
                    result = api.upload_file(
                        wiki_name,
                        file_obj,
                        entry["text"],
                        "批量上传贴图",
                        ignorewarnings=True,
                    )
                if result.get("upload", {}).get("result") != "Success":
                    raise RuntimeError(str(result))
            uploaded += 1
            existing[wiki_name.casefold()] = {"title": "File:" + wiki_name, "content": entry["text"]}
            print(f"({index}/{len(entries)}) 上传成功：{wiki_name}")
        except Exception as error:
            failed.append((wiki_name, error))
            print(f"({index}/{len(entries)}) 上传失败：{wiki_name}；{error}")

    print(f"完成：上传 {uploaded}，跳过 {skipped}，修正页面 {updated}，失败 {len(failed)}。")
    if duplicates:
        print("重复文件移动列表：")
        for duplicate, wiki_name in duplicates:
            print(f"File:{duplicate}|File:{wiki_name}")
    return {
        "uploaded": uploaded,
        "skipped": skipped,
        "updated": updated,
        "failed": failed,
        "duplicates": duplicates,
    }


if __name__ == "__main__":
    if sys.argv[1:] == ["--json"]:
        print(convert())
    elif sys.argv[1:]:
        raise SystemExit("用法：python sprites.py [--json]")
    else:
        result = upload_sprites()
        raise SystemExit(1 if result["failed"] else 0)