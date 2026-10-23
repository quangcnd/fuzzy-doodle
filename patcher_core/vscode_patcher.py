"""Module chuyên xử lý Patch VS Code (LaTeX Workshop & Code Runner C++/LaTeX)."""
from __future__ import annotations

import copy
import datetime
import json
import os
import pathlib
import shutil
from typing import Any, Dict, List, Optional, Tuple

from .env_checker import EnvironmentManager
from .ui import Colors, ctext, print_section, DEFAULT_LATEX_PROJECT


LATEX_WORKSHOP_TOOLS = [
    {
        "name": "xelatex",
        "command": "xelatex",
        "args": [
            "-shell-escape",
            "-synctex=1",
            "-interaction=nonstopmode",
            "-file-line-error",
            "%DOC%",
        ],
        "env": {},
    },
    {
        "name": "latexmk (xelatex)",
        "command": "latexmk",
        "args": [
            "-xelatex",
            "-shell-escape",
            "-synctex=1",
            "-interaction=nonstopmode",
            "-file-line-error",
            "%DOC%",
        ],
        "env": {},
    },
    {
        "name": "pdflatex",
        "command": "pdflatex",
        "args": [
            "-shell-escape",
            "-synctex=1",
            "-interaction=nonstopmode",
            "-file-line-error",
            "%DOC%",
        ],
        "env": {},
    },
]

LATEX_WORKSHOP_RECIPES = [
    {
        "name": "xelatex",
        "tools": ["xelatex"],
    },
    {
        "name": "latexmk (xelatex)",
        "tools": ["latexmk (xelatex)"],
    },
    {
        "name": "pdflatex",
        "tools": ["pdflatex"],
    },
]

CODE_RUNNER_EXECUTORS = {
    "cpp": "cd \"$dir\" && g++ -std=c++17 -O2 -Wl,--stack=67108864 \"$fileName\" -o \"$fileNameWithoutExt\" && \"$dir$fileNameWithoutExt\"",
    "latex": "cd \"$dir\" && xelatex -shell-escape -synctex=1 -interaction=nonstopmode -file-line-error \"$fileName\"",
}

DEFAULT_CODERUNNER_CPP = "cd $dir && g++ $fileName -o $fileNameWithoutExt && $dir$fileNameWithoutExt"


def clean_jsonc(text: str) -> str:
    """Loại bỏ comment `//`, `/* ... */` và dấu phẩy thừa (trailing commas) một cách an toàn,
    tuyệt đối không làm hỏng chuỗi ký tự chứa `//` hay `,}` bên trong dấu ngoặc kép.
    """
    # Bước 1: Loại bỏ comments (// và /* ... */) nhưng giữ nguyên nội dung trong chuỗi
    no_comments: List[str] = []
    i = 0
    n = len(text)
    in_string = False
    escape = False

    while i < n:
        c = text[i]

        if in_string:
            no_comments.append(c)
            if escape:
                escape = False
            elif c == '\\':
                escape = True
            elif c == '"':
                in_string = False
            i += 1
            continue

        if c == '"':
            in_string = True
            no_comments.append(c)
            i += 1
            continue

        if c == '/' and i + 1 < n:
            c2 = text[i + 1]
            if c2 == '/':
                i += 2
                while i < n and text[i] != '\n':
                    i += 1
                continue
            elif c2 == '*':
                i += 2
                while i + 1 < n and not (text[i] == '*' and text[i + 1] == '/'):
                    if text[i] == '\n':
                        no_comments.append('\n')
                    i += 1
                i += 2
                continue

        no_comments.append(c)
        i += 1

    cleaned_text = ''.join(no_comments)

    # Bước 2: Loại bỏ trailing commas ngay trước } hoặc ]
    out: List[str] = []
    i = 0
    n = len(cleaned_text)
    in_string = False
    escape = False

    while i < n:
        c = cleaned_text[i]

        if in_string:
            out.append(c)
            if escape:
                escape = False
            elif c == '\\':
                escape = True
            elif c == '"':
                in_string = False
            i += 1
            continue

        if c == '"':
            in_string = True
            out.append(c)
            i += 1
            continue

        if c == ',':
            j = i + 1
            while j < n and cleaned_text[j] in ' \t\r\n':
                j += 1
            if j < n and cleaned_text[j] in '}]':
                i += 1
                continue

        out.append(c)
        i += 1

    return ''.join(out)


class VSCodePatcher:
    """Chịu trách nhiệm patch cấu hình LaTeX Workshop và/hoặc Code Runner vào VS Code
    (User settings.json, tất cả Profiles hiện có, và Workspace `.vscode/settings.json`).
    Hỗ trợ merge an toàn tools/recipes theo `name` để không mất recipes tùy chỉnh của người dùng.
    """

    def __init__(self, env: EnvironmentManager, auto_yes: bool = False):
        self.env = env
        self.auto_yes = auto_yes

    @staticmethod
    def _load_json_safe(path: pathlib.Path) -> dict:
        if not path.is_file():
            return {}
        raw = path.read_text(encoding="utf-8", errors="replace").strip()
        if not raw:
            return {}
        cleaned = clean_jsonc(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"  {ctext('[!]', Colors.YELLOW)} Cảnh báo: File `{path}` định dạng JSONC phức tạp ({e}), thử nạp dự phòng...")
            try:
                return json.loads(raw)
            except Exception:
                raise ValueError(f"Không thể đọc JSON từ `{path}`: cú pháp không hợp lệ.")

    @classmethod
    def _merge_tools(cls, existing_tools: Any) -> List[Dict[str, Any]]:
        tools_list: List[Dict[str, Any]] = list(existing_tools) if isinstance(existing_tools, list) else []
        tool_map = {t.get("name"): idx for idx, t in enumerate(tools_list) if isinstance(t, dict)}

        for target_tool in LATEX_WORKSHOP_TOOLS:
            name = target_tool["name"]
            if name in tool_map:
                idx = tool_map[name]
                tools_list[idx] = target_tool
            else:
                tools_list.append(target_tool)
                tool_map[name] = len(tools_list) - 1
        return tools_list

    @classmethod
    def _merge_recipes(cls, existing_recipes: Any) -> List[Dict[str, Any]]:
        recipes_list: List[Dict[str, Any]] = list(existing_recipes) if isinstance(existing_recipes, list) else []
        recipe_map = {r.get("name"): idx for idx, r in enumerate(recipes_list) if isinstance(r, dict)}

        for target_recipe in LATEX_WORKSHOP_RECIPES:
            name = target_recipe["name"]
            if name in recipe_map:
                idx = recipe_map[name]
                recipes_list[idx] = target_recipe
            else:
                recipes_list.append(target_recipe)
                recipe_map[name] = len(recipes_list) - 1
        return recipes_list

    @classmethod
    def _patch_settings_file(
        cls,
        settings_path: pathlib.Path,
        patch_workshop: bool,
        patch_coderunner: bool,
    ) -> bool:
        try:
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            data = cls._load_json_safe(settings_path)
            original_data = copy.deepcopy(data)

            if patch_workshop:
                data["latex-workshop.latex.recipe.default"] = "first"
                data["latex-workshop.latex.tools"] = cls._merge_tools(data.get("latex-workshop.latex.tools"))
                data["latex-workshop.latex.recipes"] = cls._merge_recipes(data.get("latex-workshop.latex.recipes"))

            if patch_coderunner:
                exec_map = data.get("code-runner.executorMap")
                if not isinstance(exec_map, dict):
                    exec_map = {}

                exec_map["latex"] = CODE_RUNNER_EXECUTORS["latex"]

                current_cpp = exec_map.get("cpp")
                old_unquoted_cpp = "cd $dir && g++ -std=c++17 -O2 -Wl,--stack=67108864 \"$fileName\" -o \"$fileNameWithoutExt\" && \"$dir$fileNameWithoutExt\""
                if not current_cpp or current_cpp == DEFAULT_CODERUNNER_CPP or current_cpp == CODE_RUNNER_EXECUTORS["cpp"] or current_cpp == old_unquoted_cpp:
                    exec_map["cpp"] = CODE_RUNNER_EXECUTORS["cpp"]
                else:
                    print(f"  {ctext('[i]', Colors.CYAN)} Executor 'cpp' của bạn đang tùy biến riêng: `{current_cpp}`. Giữ nguyên cấu hình của bạn.")

                data["code-runner.executorMap"] = exec_map
                data.setdefault("code-runner.runInTerminal", True)
                data.setdefault("code-runner.saveFileBeforeRun", True)

            if settings_path.is_file() and data == original_data:
                return True

            if settings_path.is_file():
                bak_path = settings_path.with_suffix(".json.bak")
                if not bak_path.exists():
                    shutil.copy2(settings_path, bak_path)
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                shutil.copy2(settings_path, settings_path.with_name(f"{settings_path.name}.bak.{ts}"))

            tmp_path = settings_path.with_name(f"{settings_path.name}.tmp")
            try:
                tmp_path.write_text(
                    json.dumps(data, indent=4, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                os.replace(tmp_path, settings_path)
            finally:
                if tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except OSError:
                        pass

            return True
        except Exception as e:
            print(f"  {ctext('[✘]', Colors.RED)} Lỗi khi cập nhật `{settings_path}`: {e}")
            return False

    def run_patch(
        self,
        patch_workshop: Optional[bool] = None,
        patch_coderunner: Optional[bool] = None,
        target_workspace: Optional[str] = None,
    ) -> bool:
        print_section("CHẾ ĐỘ PATCH 2: PATCH VS CODE (LATEX WORKSHOP & CODE RUNNER)")

        if patch_workshop is None and patch_coderunner is None:
            if self.auto_yes:
                patch_workshop, patch_coderunner = True, True
            else:
                print("  Chọn thành phần VS Code bạn muốn patch:")
                print(f"    {ctext('[1]', Colors.CYAN)} Patch cả {ctext('LaTeX Workshop', Colors.BOLD)} + {ctext('Code Runner (C++ & LaTeX)', Colors.BOLD)} (Khuyên dùng)")
                print(f"    {ctext('[2]', Colors.CYAN)} Chỉ patch {ctext('LaTeX Workshop', Colors.BOLD)} (`xelatex -shell-escape` mặc định)")
                print(f"    {ctext('[3]', Colors.CYAN)} Chỉ patch {ctext('Code Runner', Colors.BOLD)} (Chạy nhanh C++ & LaTeX)")
                sub_choice = input("  Lựa chọn của bạn [1/2/3, mặc định=1]: ").strip()
                if sub_choice == "2":
                    patch_workshop, patch_coderunner = True, False
                elif sub_choice == "3":
                    patch_workshop, patch_coderunner = False, True
                else:
                    patch_workshop, patch_coderunner = True, True

        appdata = os.environ.get("APPDATA", "")
        target_files: List[Tuple[str, pathlib.Path]] = []

        if appdata:
            code_user_dir = pathlib.Path(appdata) / "Code" / "User"
            if code_user_dir.is_dir():
                target_files.append(("VS Code User Settings", code_user_dir / "settings.json"))
                profiles_dir = code_user_dir / "profiles"
                if profiles_dir.is_dir():
                    for prof_folder in profiles_dir.iterdir():
                        if prof_folder.is_dir():
                            target_files.append((f"VS Code Profile ({prof_folder.name})", prof_folder / "settings.json"))

        if not target_files:
            print(f"  {ctext('[!]', Colors.YELLOW)} Không tìm thấy thư mục cấu hình `%APPDATA%\\Code\\User`.")

        patch_success = True
        for label, s_path in target_files:
            if self._patch_settings_file(s_path, bool(patch_workshop), bool(patch_coderunner)):
                print(f"  {ctext('[✔]', Colors.GREEN)} Đã patch {label:<32}: {s_path}")
            else:
                patch_success = False

        ws_path: Optional[pathlib.Path] = None
        if target_workspace:
            cleaned_ws = str(target_workspace).strip().strip('"')
            cand = pathlib.Path(cleaned_ws).resolve()
            if cand.is_dir():
                ws_path = cand
            else:
                print(f"  {ctext('[!]', Colors.YELLOW)} Thư mục chỉ định `--workspace` không tồn tại: {target_workspace}")
        elif self.auto_yes:
            # Trong chế độ --yes, không tự ý ghi vào repo hay project khi chưa có target_workspace rõ ràng
            print(f"  {ctext('[i]', Colors.CYAN)} Chế độ --yes: không có `--workspace`, bỏ qua bước patch Workspace `.vscode/settings.json`.")
        else:
            hint = f" (Enter = `{DEFAULT_LATEX_PROJECT}`)" if DEFAULT_LATEX_PROJECT else ""
            ans = input("  Bạn có muốn áp dụng cấu hình này vào `.vscode/settings.json` của 1 thư mục Workspace cụ thể không? [y/N]: ").strip().lower()
            if ans in ("y", "yes"):
                raw_ws = input(f"  Nhập đường dẫn thư mục Workspace{hint} (hoặc Enter để bỏ qua): ").strip().strip('"')
                if raw_ws:
                    p = pathlib.Path(raw_ws).resolve()
                    if p.is_dir():
                        ws_path = p
                    else:
                        print(f"  {ctext('[!]', Colors.YELLOW)} Thư mục không tồn tại: `{p}`")
                elif DEFAULT_LATEX_PROJECT:
                    ws_path = DEFAULT_LATEX_PROJECT

        if ws_path and ws_path.is_dir():
            ws_settings = ws_path / ".vscode" / "settings.json"
            if self._patch_settings_file(ws_settings, bool(patch_workshop), bool(patch_coderunner)):
                print(f"  {ctext('[✔]', Colors.GREEN)} Đã patch Workspace Settings          : {ws_settings}")
            else:
                patch_success = False

        if not target_files and not (ws_path and ws_path.is_dir()):
            print(f"  {ctext('[✘]', Colors.RED)} Không tìm thấy bất kỳ file cấu hình VS Code nào để patch.")
            return False

        return patch_success
