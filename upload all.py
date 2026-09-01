import importlib.util
import sys
import traceback
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
    return "WIKI_JSON_TITLE" in text and "def convert" in text


def discover_scripts():
    return sorted(path for path in BASE_DIR.glob("*.py") if is_converter_script(path))


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
    module = load_module(path)
    title = getattr(module, "WIKI_JSON_TITLE", "未知 JSON 页面")
    convert = getattr(module, "convert", None)
    if not callable(convert):
        raise RuntimeError(f"{path.name} 没有可调用的 convert 函数")

    print("=" * 60)
    print(f"脚本：{path.name}")
    print(f"目标：{title}")
    print("=" * 60)

    text = convert()
    if not isinstance(text, str):
        raise RuntimeError(f"{path.name} 的 convert() 必须返回字符串")
    login.upload_text(title, text, f"via {path.name}")
    print(f"上传成功：{title}")
    return title


def main():
    scripts = discover_scripts()

    if not scripts:
        print("没有发现可运行的上传脚本。")
        print("脚本需要定义 WIKI_JSON_TITLE 和 convert()。")
        return 1

    print("将运行以下脚本：")
    for path in scripts:
        print(" - " + path.name)

    ok = []
    failed = []
    for path in scripts:
        try:
            title = run_script(path)
            ok.append((path.name, title))
        except Exception as error:
            failed.append((path.name, error))
            print(f"失败：{path.name}: {error}")
            traceback.print_exc()

    print("=" * 60)
    print("执行汇总")
    print("=" * 60)
    for name, title in ok:
        print(f"成功：{name} -> {title}")
    for name, error in failed:
        print(f"失败：{name} -> {error}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())