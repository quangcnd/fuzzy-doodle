"""Module chuyên xử lý Patch VS Code (LaTeX Workshop & Code Runner C++/LaTeX)."""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
from typing import List, Optional, Tuple

from .env_checker import EnvironmentManager
from .ui import Colors, ctext, print_section, DEFAULT_LATEX_PROJECT


LATEX_WORKSHOP_SETTINGS = {
    "latex-workshop.latex.recipe.default": "first",
    "latex-workshop.latex.tools": [
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
    ],
    "latex-workshop.latex.recipes": [
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
    ],
}

CODE_RUNNER_EXECUTORS = {
    "cpp": "cd $dir && g++ -std=c++17 -O2 -Wl,--stack=67108864 \"$fileName\" -o \"$fileNameWithoutExt\" && \"$dir$fileNameWithoutExt\"",
    "latex": "cd $dir && xelatex -shell-escape -synctex=1 -interaction=nonstopmode -file-line-error \"$fileName\"",
}


class VSCodePatcher:
    """Chịu trách nhiệm patch cấu hình LaTeX Workshop và/hoặc Code Runner vào VS Code
    (User settings.json, tất cả Profiles hiện có, và Workspace `.vscode/settings.json`).
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
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            cleaned = re.sub(r",(\s*[\]}])", r"\1", raw)
            return json.loads(cleaned)

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

            if settings_path.is_file():
                bak_path = settings_path.with_suffix(".json.bak")
                if not bak_path.exists():
                    shutil.copy2(settings_path, bak_path)

            if patch_workshop:
                for k, v in LATEX_WORKSHOP_SETTINGS.items():
                    data[k] = v

            if patch_coderunner:
                exec_map = data.get("code-runner.executorMap")
                if not isinstance(exec_map, dict):
                    exec_map = {}
                exec_map["latex"] = CODE_RUNNER_EXECUTORS["latex"]
                if "cpp" not in exec_map or exec_map["cpp"] == "cd $dir && g++ $fileName -o $fileNameWithoutExt && $dir$fileNameWithoutExt":
                    exec_map["cpp"] = CODE_RUNNER_EXECUTORS["cpp"]
                data["code-runner.executorMap"] = exec_map
                data.setdefault("code-runner.runInTerminal", True)
                data.setdefault("code-runner.saveFileBeforeRun", True)

            settings_path.write_text(
                json.dumps(data, indent=4, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
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

        for label, s_path in target_files:
            if self._patch_settings_file(s_path, bool(patch_workshop), bool(patch_coderunner)):
                print(f"  {ctext('[✔]', Colors.GREEN)} Đã patch {label:<32}: {s_path}")

        ws_path: Optional[pathlib.Path] = None
        if target_workspace:
            ws_path = pathlib.Path(target_workspace).resolve()
        elif self.auto_yes:
            if DEFAULT_LATEX_PROJECT.is_dir():
                ws_path = DEFAULT_LATEX_PROJECT
        else:
            default_hint = f" (Enter = `{DEFAULT_LATEX_PROJECT}`)" if DEFAULT_LATEX_PROJECT.is_dir() else ""
            ans = input("  Bạn có muốn áp dụng cấu hình này vào `.vscode/settings.json` của 1 thư mục Workspace cụ thể không? [Y/n]: ").strip().lower()
            if ans in ("", "y", "yes"):
                raw_ws = input(f"  Nhập đường dẫn thư mục Workspace{default_hint}: ").strip().strip('"')
                if not raw_ws and DEFAULT_LATEX_PROJECT.is_dir():
                    ws_path = DEFAULT_LATEX_PROJECT
                elif raw_ws:
                    ws_path = pathlib.Path(raw_ws).resolve()

        if ws_path and ws_path.is_dir():
            ws_settings = ws_path / ".vscode" / "settings.json"
            if self._patch_settings_file(ws_settings, bool(patch_workshop), bool(patch_coderunner)):
                print(f"  {ctext('[✔]', Colors.GREEN)} Đã patch Workspace Settings          : {ws_settings}")

        return True
