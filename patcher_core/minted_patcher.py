"""Module chuyên xử lý Patch Minted / Pygments C++ / LaTeX (MiKTeX)."""
from __future__ import annotations

import pathlib
import shutil
import zipfile
from typing import Optional

from .env_checker import EnvironmentManager
from .ui import (
    Colors,
    ctext,
    print_section,
    PALENIGHT_SRC_DIR,
    TEMPLATES_LIB_DIR,
    DEFAULT_LATEX_PROJECT,
)


CPP_LEXER_HOOK = """

# Kích hoạt C++ Semantic Highlighting & Rainbow Brackets (VS Code Palenight)
try:
    from pygments.styles.palenight import _patch_cpp_lexer
    _patch_cpp_lexer()
except Exception:
    pass
"""


class MintedPygmentsPatcher:
    """Chịu trách nhiệm patch Pygments (C++ Semantic, Rainbow Brackets, Indent-Rainbow),
    đồng bộ với MiKTeX (`latexminted.py` & `pygments-*.whl`) và cập nhật mẫu `lib/codebox.tex`.
    """

    def __init__(self, env: EnvironmentManager, auto_yes: bool = False):
        self.env = env
        self.auto_yes = auto_yes

    def run_patch(self, target_latex_dir: Optional[str] = None, skip_template_sync: bool = False) -> bool:
        print_section("CHẾ ĐỘ PATCH 1: PATCH MINTED / PYGMENTS C++ / LATEX (MIKTEX)")

        if not PALENIGHT_SRC_DIR.is_dir():
            print(f"  {ctext('[✘]', Colors.RED)} Không tìm thấy thư mục nguồn `{PALENIGHT_SRC_DIR}`!")
            return False

        # 1. Tìm thư mục cài đặt pygments trong site-packages
        try:
            import pygments
            pygments_dir = pathlib.Path(pygments.__file__).resolve().parent
        except ImportError:
            print(f"  {ctext('[✘]', Colors.RED)} Chưa thể nạp thư viện `pygments`. Vui lòng kiểm tra lại cài đặt Python.")
            return False

        print(f"  {ctext('[i]', Colors.CYAN)} Thư mục Pygments của Python: {pygments_dir}")

        # 2. Copy palenight.py và palenight_ext/ vào pygments/styles/
        styles_dir = pygments_dir / "styles"
        target_palenight_py = styles_dir / "palenight.py"
        target_ext_dir = styles_dir / "palenight_ext"

        shutil.copy2(PALENIGHT_SRC_DIR / "palenight.py", target_palenight_py)
        if target_ext_dir.exists():
            shutil.rmtree(target_ext_dir)
        shutil.copytree(
            PALENIGHT_SRC_DIR / "palenight_ext",
            target_ext_dir,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        print(f"  {ctext('[✔]', Colors.GREEN)} Đã cài đặt `palenight.py` và bộ module `palenight_ext/` vào `{styles_dir}`.")

        # 3. Patch hook vào cuối file pygments/lexers/c_cpp.py
        cpp_lexer_file = pygments_dir / "lexers" / "c_cpp.py"
        if cpp_lexer_file.is_file():
            content = cpp_lexer_file.read_text(encoding="utf-8")
            if "_patch_cpp_lexer" not in content:
                bak_file = cpp_lexer_file.with_suffix(".py.bak")
                if not bak_file.exists():
                    shutil.copy2(cpp_lexer_file, bak_file)
                cpp_lexer_file.write_text(content.rstrip() + "\n" + CPP_LEXER_HOOK, encoding="utf-8")
                print(f"  {ctext('[✔]', Colors.GREEN)} Đã gắn hook C++ Semantic & Rainbow Brackets vào `{cpp_lexer_file}`.")
            else:
                print(f"  {ctext('[✔]', Colors.GREEN)} File `{cpp_lexer_file.name}` đã có sẵn hook `_patch_cpp_lexer()`.")
        else:
            print(f"  {ctext('[✘]', Colors.RED)} Không tìm thấy file `{cpp_lexer_file}`!")
            return False

        # 4. Patch MiKTeX: scripts/minted/latexminted.py và pygments-*.whl
        self._patch_miktex_minted(pygments_dir)

        # 5. Hỏi cập nhật mẫu lib/codebox.tex và xóa cache _minted
        if not skip_template_sync:
            self._offer_latex_template_sync(target_latex_dir)

        return True

    def _patch_miktex_minted(self, pygments_dir: pathlib.Path) -> None:
        if not self.env.miktex_root_dir:
            print(f"  {ctext('[!]', Colors.YELLOW)} Không tìm thấy thư mục gốc MiKTeX, bỏ qua bước đồng bộ `.whl` nội bộ của MiKTeX.")
            return

        minted_scripts_dir = self.env.miktex_root_dir / "scripts" / "minted"
        if not minted_scripts_dir.is_dir():
            print(f"  {ctext('[!]', Colors.YELLOW)} Không tìm thấy `{minted_scripts_dir}` (Gói `minted` có thể chưa được giải nén trong MiKTeX).")
            return

        # 4a. Patch latexminted.py để ưu tiên site-packages của Python trước file .whl
        latexminted_py = minted_scripts_dir / "latexminted.py"
        if latexminted_py.is_file():
            lm_text = latexminted_py.read_text(encoding="utf-8")
            old_block = (
                "for wheel_path in wheel_paths:\n"
                "    sys.path.insert(0, wheel_path.as_posix())"
            )
            new_block = (
                "for wheel_path in wheel_paths:\n"
                "    if wheel_path.name.startswith('pygments'):\n"
                "        sys.path.append(wheel_path.as_posix())\n"
                "    else:\n"
                "        sys.path.insert(0, wheel_path.as_posix())"
            )
            if old_block in lm_text:
                bak_lm = latexminted_py.with_suffix(".py.bak")
                if not bak_lm.exists():
                    shutil.copy2(latexminted_py, bak_lm)
                latexminted_py.write_text(lm_text.replace(old_block, new_block), encoding="utf-8")
                print(f"  {ctext('[✔]', Colors.GREEN)} Đã patch `{latexminted_py}` (ưu tiên nạp `pygments` từ `site-packages`).")
            elif "wheel_path.name.startswith('pygments')" in lm_text:
                print(f"  {ctext('[✔]', Colors.GREEN)} File `{latexminted_py.name}` của MiKTeX đã được patch từ trước.")
            else:
                print(f"  {ctext('[i]', Colors.CYAN)} Cấu trúc `{latexminted_py.name}` khác mặc định, tiếp tục đồng bộ trực tiếp vào `.whl`.")

        # 4b. Đồng bộ trực tiếp vào file pygments-*.whl nội bộ của MiKTeX
        whl_files = list(minted_scripts_dir.glob("pygments-*.whl"))
        for whl_path in whl_files:
            try:
                bak_whl = whl_path.with_suffix(".whl.bak")
                if not bak_whl.exists():
                    shutil.copy2(whl_path, bak_whl)

                tmp_whl = whl_path.with_suffix(".whl.tmp")
                skip_entries = {"pygments/styles/palenight.py", "pygments/lexers/c_cpp.py"}

                with zipfile.ZipFile(whl_path, "r") as zin, zipfile.ZipFile(tmp_whl, "w", zipfile.ZIP_DEFLATED) as zout:
                    for item in zin.infolist():
                        if item.filename in skip_entries or item.filename.startswith("pygments/styles/palenight_ext/"):
                            continue
                        zout.writestr(item, zin.read(item.filename))

                    zout.write(pygments_dir / "styles" / "palenight.py", "pygments/styles/palenight.py")
                    zout.write(pygments_dir / "lexers" / "c_cpp.py", "pygments/lexers/c_cpp.py")
                    ext_dir = pygments_dir / "styles" / "palenight_ext"
                    for py_file in ext_dir.glob("*.py"):
                        zout.write(py_file, f"pygments/styles/palenight_ext/{py_file.name}")

                shutil.move(str(tmp_whl), str(whl_path))
                print(f"  {ctext('[✔]', Colors.GREEN)} Đã đồng bộ `palenight_ext` & `c_cpp.py` vào gói nén MiKTeX: `{whl_path.name}`.")
            except PermissionError:
                print(f"  {ctext('[!]', Colors.YELLOW)} Không đủ quyền ghi đè `{whl_path}` (Hãy chạy Terminal với quyền Administrator nếu cần).")
            except Exception as e:
                print(f"  {ctext('[!]', Colors.YELLOW)} Lỗi khi cập nhật `{whl_path.name}`: {e}")

    def _offer_latex_template_sync(self, target_latex_dir: Optional[str] = None) -> None:
        if not TEMPLATES_LIB_DIR.is_dir():
            return

        default_proj = pathlib.Path(target_latex_dir) if target_latex_dir else DEFAULT_LATEX_PROJECT
        print(f"\n  {ctext('📄 Đồng bộ mẫu LaTeX (`lib/codebox.tex`) & dọn cache `_minted`:', Colors.BOLD)}")

        proj_path: Optional[pathlib.Path] = None
        if self.auto_yes:
            if default_proj.is_dir():
                proj_path = default_proj
        else:
            default_hint = f" (Enter = `{default_proj}`)" if default_proj.is_dir() else ""
            ans = input("  Bạn có muốn cập nhật/xuất `lib/codebox.tex` vào thư mục Project LaTeX không? [Y/n]: ").strip().lower()
            if ans in ("", "y", "yes"):
                raw_dir = input(f"  Nhập đường dẫn thư mục Project LaTeX{default_hint}: ").strip().strip('"')
                if not raw_dir and default_proj.is_dir():
                    proj_path = default_proj
                elif raw_dir:
                    proj_path = pathlib.Path(raw_dir).resolve()

        if proj_path:
            lib_dir = proj_path / "lib"
            lib_dir.mkdir(parents=True, exist_ok=True)

            src_codebox = TEMPLATES_LIB_DIR / "codebox.tex"
            dst_codebox = lib_dir / "codebox.tex"
            if dst_codebox.is_file():
                if dst_codebox.read_text(encoding="utf-8") != src_codebox.read_text(encoding="utf-8"):
                    shutil.copy2(dst_codebox, dst_codebox.with_suffix(".tex.bak"))
            shutil.copy2(src_codebox, dst_codebox)
            print(f"  {ctext('[✔]', Colors.GREEN)} Đã cập nhật `{dst_codebox}`.")

            for tpl_file in TEMPLATES_LIB_DIR.glob("*.tex"):
                if tpl_file.name == "codebox.tex":
                    continue
                dst_tpl = lib_dir / tpl_file.name
                if not dst_tpl.exists():
                    shutil.copy2(tpl_file, dst_tpl)
                    print(f"  {ctext('[✔]', Colors.GREEN)} Đã tạo mới file mẫu `{dst_tpl}`.")

            minted_cache = proj_path / "_minted"
            if minted_cache.is_dir():
                shutil.rmtree(minted_cache, ignore_errors=True)
                print(f"  {ctext('[✔]', Colors.GREEN)} Đã dọn sạch thư mục cache cũ `{minted_cache}`.")
