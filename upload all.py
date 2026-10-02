import importlib.util
import sys
from pathlib import Path

import login


BASE_DIR = Path(__file__).resolve().parent

EXCLUDED = {
    "login.py",
    "upload all.py",
    "upload_all.py",
}


def is_converter_script(path: Path) -> bool:
    if path.name in EXCLUDED:
        return False
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="gb18030", errors="ignore")
    return ("WIKI_JSON_TITLE" in text or "WIKI_TITLE" in text) and "def convert" in text


def discover_scripts():
    return sorted(path for path in BASE_DIR.glob("*.py") if is_converter_script(path)) + sorted(BASE_DIR.glob("*.lua"))


def load_module(path: Path):
    module_name = "_upload_all_" + path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载脚本：{path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_script(path: Path):
    if path.suffix.lower() == ".lua":
        title = "Module:" + path.stem
        text = path.read_text(encoding="utf-8-sig")
        login.upload_text(title, text, f"via {path.name}")
        return title

    module = load_module(path)
    title = getattr(module, "WIKI_JSON_TITLE", None) or getattr(module, "WIKI_TITLE", "未知 JSON 页面")
    convert = getattr(module, "convert", None)
    if not callable(convert):
        raise RuntimeError(f"{path.name} 没有可调用的 convert 函数")

    text = convert()
    if not isinstance(text, str):
        raise RuntimeError(f"{path.name} 的 convert() 必须返回字符串")
    login.upload_text(title, text, f"via {path.name}")
    return title


def main():
    scripts = discover_scripts()

    if not scripts:
        print("失败：没有发现可上传的文件。")
        print("成功：0")
        print("失败：0")
        return 1

    ok = []
    failed = []
    for path in scripts:
        try:
            title = run_script(path)
            ok.append((path.name, title))
            print(f"成功：{path.name} -> {title}")
        except Exception as error:
            failed.append((path.name, error))
            print(f"失败：{path.name} -> {error}")

    print(f"成功：{len(ok)}")
    print(f"失败：{len(failed)}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())